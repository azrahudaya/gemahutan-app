import hmac
import logging
import secrets
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.deps import get_db, security_optional
from app.models.tables import User, UserRole
from app.schemas.auth import (
    ActivateAccountRequest,
    ForgotPasswordRequest,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserResponse,
)
from app.services import audit, mailer, password_reset, tamu
from app.services.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    token_masih_berlaku,
    verify_password,
)
from app.services.security import (
    LOGIN_LIMIT,
    clear_login_failures,
    is_token_revoked,
    login_blocked_for,
    login_identifier,
    register_login_failure,
    revoke_token,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

logger = logging.getLogger(__name__)


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(
    body: RegisterRequest, request: Request, db: AsyncSession = Depends(get_db)
):
    settings = get_settings()
    if not settings.allow_registration or settings.environment == "production":
        raise HTTPException(
            status_code=403,
            detail="Pendaftaran akun ditutup. Hubungi pengelola untuk dibuatkan akun.",
        )

    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar():
        raise HTTPException(status_code=409, detail="Email sudah terdaftar")

    user = User(
        email=body.email,
        password_hash=hash_password(body.password),
        name=(body.name or "").strip()[:255] or None,
    )
    db.add(user)
    await db.flush()
    await audit.catat(
        db,
        "auth.register",
        actor=user,
        entity_type="user",
        entity_id=user.id,
        detail={"role": user.role.value},
        request=request,
    )
    await db.commit()
    await db.refresh(user)
    return UserResponse(
        id=user.id,
        email=user.email,
        role=user.role.value,
        created_at=user.created_at.isoformat(),
    )


@router.post("/tamu", response_model=TokenResponse, include_in_schema=False)
async def buat_tamu(request: Request, db: AsyncSession = Depends(get_db)):
    """Buat akun tamu baru untuk satu pengunjung halaman depan.

    Hanya server web yang boleh memanggil ini: ia membawa TAMU_RAHASIA dan IP
    pengunjung aslinya. Pemanggil lain dijawab 404 seolah endpoint tidak ada.
    """
    settings = get_settings()
    rahasia = request.headers.get("x-tamu-rahasia", "")
    if (
        not settings.tamu_aktif
        or not settings.tamu_rahasia
        or not hmac.compare_digest(rahasia, settings.tamu_rahasia)
    ):
        raise HTTPException(404, "Tidak ditemukan")

    ip = request.headers.get("x-pengunjung-ip", "").split(",")[0].strip() or "tanpa-ip"
    from app.services.security import _client

    kunci = f"gemahutan:tamu:{ip}"
    redis = _client()
    jumlah = await redis.incr(kunci)
    if jumlah == 1:
        await redis.expire(kunci, 3600)
    if jumlah > settings.tamu_batas_per_jam:
        raise HTTPException(429, "Terlalu banyak sesi baru dari jaringan ini. Coba lagi nanti.")

    user = User(
        email=tamu.email_tamu_baru(),
        password_hash=hash_password(secrets.token_urlsafe(32)),
        name="Tamu",
        role=UserRole.ranger,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return TokenResponse(
        access_token=create_access_token(user.id, user.role.value, user.token_version),
        refresh_token=create_refresh_token(user.id, user.token_version),
    )


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    identifier = login_identifier(body.email, request.client.host if request.client else None)

    blocked_for = await login_blocked_for(identifier)
    if blocked_for:
        raise HTTPException(
            status_code=429,
            detail=(
                f"Terlalu banyak percobaan login gagal. Coba lagi dalam {blocked_for} detik."
            ),
            headers={"Retry-After": str(blocked_for)},
        )

    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar()
    if not user or not user.is_active or not verify_password(body.password, user.password_hash):
        count = await register_login_failure(identifier)
        sisa = max(0, LOGIN_LIMIT - count)
        # Percobaan gagal disimpan dan di-commit lebih dulu: setelah HTTPException
        # dilempar, sesinya dibatalkan, jadi baris audit harus sudah tersimpan.
        #
        # Pelakunya sengaja TIDAK diisi walau akunnya ada. Sandi yang salah tidak
        # membuktikan pemilik akun yang mengetik, jadi mencatatnya sebagai pelaku
        # akan membuat jejaknya berbunyi seolah pemilik akun sedang aktif.
        # Akun yang disasar tetap dicatat sebagai entity, karena itu memang
        # informasi yang dicari saat menelusuri percobaan berulang.
        await audit.catat(
            db,
            "auth.login_gagal",
            actor=None,
            entity_type="user",
            entity_id=user.id if user else None,
            detail={"email_dicoba": body.email, "ada_akun": bool(user)},
            request=request,
        )
        await db.commit()
        raise HTTPException(
            status_code=401,
            detail=(
                "Email atau kata sandi salah."
                + (f" Sisa {sisa} percobaan sebelum akun dikunci sementara." if 0 < sisa <= 2 else "")
            ),
        )

    await clear_login_failures(identifier)
    await audit.catat(
        db,
        "auth.login",
        actor=user,
        entity_type="user",
        entity_id=user.id,
        detail={"role": user.role.value},
        request=request,
    )
    await db.commit()
    return TokenResponse(
        access_token=create_access_token(user.id, user.role.value, user.token_version),
        refresh_token=create_refresh_token(user.id, user.token_version),
    )


@router.post("/forgot-password", status_code=202)
async def forgot_password(
    body: ForgotPasswordRequest, request: Request, db: AsyncSession = Depends(get_db)
):
    """Kirim tautan atur ulang kalau alamatnya terdaftar.

    Jawabannya SELALU sama, baik alamatnya terdaftar maupun tidak. Kalau
    jawabannya berbeda, endpoint ini berubah jadi alat untuk memeriksa email mana
    yang punya akun di sistem ini.

    Keterbatasan yang disadari: pengirimannya memakan waktu berbeda antara alamat
    yang ada dan yang tidak, jadi selisih waktunya masih bisa diamati. Untuk
    menutupnya perlu jeda tetap atau pengiriman asinkron, dan itu belum dipakai
    di sini.
    """
    pesan = {
        "message": (
            "Kalau alamat email itu terdaftar, tautan atur ulang sandi sudah "
            "dikirim. Periksa kotak masuk dan folder spam."
        )
    }

    hasil = await db.execute(select(User).where(User.email == body.email))
    user = hasil.scalar()
    if not user or not user.is_active:
        return pesan

    mentah, kedaluwarsa = await password_reset.buat_token(
        db, user, audit.ip_dari_request(request)
    )
    await audit.catat(
        db,
        "auth.reset_diminta",
        actor=user,
        entity_type="user",
        entity_id=user.id,
        detail={"kedaluwarsa": kedaluwarsa.isoformat()},
        request=request,
    )
    await db.commit()

    terkirim = await mailer.kirim_tautan_reset(
        user.email,
        password_reset.tautan_reset(mentah),
        get_settings().reset_token_minutes,
    )
    if not terkirim:
        logger.error("Tautan atur ulang untuk %s tidak terkirim", user.email)

    return pesan


@router.post("/reset-password")
async def reset_password(
    body: ResetPasswordRequest, request: Request, db: AsyncSession = Depends(get_db)
):
    """Pakai token sekali pakai untuk mengganti sandi.

    Token diambil dari email, jadi isinya diperlakukan sebagai rahasia: pesan
    kesalahannya tidak membedakan token yang salah dengan token yang kedaluwarsa,
    supaya tidak memberi tahu penebak apakah tokennya pernah ada.
    """
    gagal = HTTPException(
        status_code=400,
        detail=(
            "Tautan atur ulang tidak berlaku atau sudah kedaluwarsa. "
            "Minta tautan baru dari halaman lupa sandi."
        ),
    )

    baris = await password_reset.cari_token_valid(db, body.token)
    if not baris:
        raise gagal

    hasil = await db.execute(select(User).where(User.id == baris.user_id))
    user = hasil.scalar()
    if not user or not user.is_active:
        raise gagal

    sekarang = datetime.now(UTC)
    user.password_hash = hash_password(body.password)
    # Versi dinaikkan satu. Semua token lama langsung tidak cocok, jadi setiap
    # sesi yang sudah ada berakhir. Tanpa langkah ini, siapa pun yang sudah masuk
    # dengan sandi lama tetap bisa memakai tokennya, sehingga pemulihan akunnya
    # tidak benar-benar memulihkan apa pun.
    user.token_version = int(user.token_version or 0) + 1
    baris.used_at = sekarang
    # Token lain yang belum dipakai ikut dimatikan, supaya tidak ada tautan lama
    # yang masih berlaku setelah sandinya diganti.
    dibatalkan = await password_reset.batalkan_token_lama(db, user.id)

    await audit.catat(
        db,
        "auth.reset_selesai",
        actor=user,
        entity_type="user",
        entity_id=user.id,
        detail={"token_lain_dibatalkan": dibatalkan},
        request=request,
    )
    await db.commit()

    return {
        "message": "Sandi berhasil diganti. Silakan masuk dengan sandi baru.",
        "sessions_revoked": True,
    }


@router.post("/aktivasi")
async def aktivasi_akun(
    body: ActivateAccountRequest, request: Request, db: AsyncSession = Depends(get_db)
):
    """Aktifkan akun undangan dengan membuat sandi pertama.

    Berbeda dari atur ulang sandi: akunnya belum aktif, jadi pemeriksaan
    `is_active` justru dilonggarkan di sini, dan akun diaktifkan begitu sandinya
    dibuat.
    """
    gagal = HTTPException(
        status_code=400,
        detail=(
            "Tautan undangan tidak berlaku atau sudah kedaluwarsa. "
            "Minta admin mengirim undangan baru."
        ),
    )

    baris = await password_reset.cari_token_valid(db, body.token)
    if not baris:
        raise gagal

    hasil = await db.execute(select(User).where(User.id == baris.user_id))
    user = hasil.scalar()
    if not user:
        raise gagal
    if user.is_active:
        raise HTTPException(409, "Akun sudah aktif. Silakan masuk.")

    sekarang = datetime.now(UTC)
    user.password_hash = hash_password(body.password)
    user.is_active = True
    user.token_version = int(user.token_version or 0) + 1
    baris.used_at = sekarang
    dibatalkan = await password_reset.batalkan_token_lama(db, user.id)

    await audit.catat(
        db,
        "auth.aktivasi",
        actor=user,
        entity_type="user",
        entity_id=user.id,
        detail={"token_lain_dibatalkan": dibatalkan},
        request=request,
    )
    await db.commit()

    return {"message": "Akun aktif. Silakan masuk dengan sandi baru."}


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    try:
        payload = decode_token(body.refresh_token)
    except Exception:
        raise HTTPException(status_code=401, detail="Refresh token tidak valid") from None

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Jenis token tidak valid")

    # Refresh token yang sudah dicabut saat logout tidak boleh menukar token baru.
    if await is_token_revoked(payload):
        raise HTTPException(
            status_code=401, detail="Token sudah dicabut, silakan login ulang"
        )

    user_id = int(payload["sub"])
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar()
    if not user:
        raise HTTPException(status_code=401, detail="Pengguna tidak ditemukan")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Akun tidak aktif")

    # Sesi dari sebelum sandi diganti tidak boleh bisa menukar token baru. Tanpa
    # pemeriksaan ini, aturan versi token bisa dilewati lewat /refresh.
    if not token_masih_berlaku(payload, user.token_version):
        raise HTTPException(
            status_code=401,
            detail="Sesi sudah berakhir karena sandi diganti. Silakan masuk ulang.",
        )

    # Rotasi refresh token: token lama dicabut sebelum token baru diterbitkan.
    # Token reuse berikutnya akan ditolak oleh pemeriksaan revocation di atas.
    await revoke_token(body.refresh_token)

    return TokenResponse(
        access_token=create_access_token(user.id, user.role.value, user.token_version),
        refresh_token=create_refresh_token(user.id, user.token_version),
    )


@router.post("/logout")
async def logout(
    request: Request,
    body: LogoutRequest | None = None,
    credentials: HTTPAuthorizationCredentials | None = Depends(security_optional),
    db: AsyncSession = Depends(get_db),
):
    """Cabut token yang sedang dipakai, dan refresh token kalau dikirim.

    Token yang sudah dicabut tidak bisa dipakai lagi walau belum kedaluwarsa,
    karena jti-nya dicatat di Redis sampai masa berlakunya habis.
    """
    revoked = 0
    if credentials and credentials.credentials:
        revoked += int(await revoke_token(credentials.credentials))
    if body and body.refresh_token:
        revoked += int(await revoke_token(body.refresh_token))

    # Pelaku diambil dari token yang dicabut. Token yang tidak bisa dibaca tetap
    # dicatat tanpa pelaku, karena percobaan logout dengan token rusak juga
    # termasuk hal yang perlu terlihat.
    pelaku = None
    if credentials and credentials.credentials:
        try:
            isi = decode_token(credentials.credentials)
            hasil = await db.execute(select(User).where(User.id == int(isi["sub"])))
            pelaku = hasil.scalar()
        except Exception:  # noqa: BLE001 - token rusak bukan alasan menggagalkan logout
            pelaku = None
    await audit.catat(
        db,
        "auth.logout",
        actor=pelaku,
        entity_type="user",
        entity_id=pelaku.id if pelaku else None,
        detail={"token_dicabut": revoked},
        request=request,
    )
    await db.commit()

    return {
        "message": "Logged out successfully",
        "tokens_revoked": revoked,
    }
