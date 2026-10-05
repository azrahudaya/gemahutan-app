from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory
from app.services import tamu
from app.services.auth import decode_token, token_masih_berlaku

security = HTTPBearer(auto_error=False)
security_optional = HTTPBearer(auto_error=False)


async def get_db() -> AsyncSession:
    async with async_session_factory() as session:
        yield session


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db),
):
    # Permintaan tanpa token dijawab 401, bukan 403. 403 dipakai khusus untuk
    # akun yang sudah masuk tetapi perannya tidak cukup.
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=401,
            detail="Token tidak ada",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = await _resolve_user(credentials.credentials, db)
    await tamu.jaga(request, user, db)
    return user


async def get_current_user_flexible(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security_optional),
    db: AsyncSession = Depends(get_db),
):
    """Auth untuk endpoint yang dipanggil elemen HTML, misal tag <audio>.

    Browser tidak bisa menyetel header Authorization pada <audio src>, jadi token
    boleh dikirim lewat query string. Header tetap diprioritaskan.
    """
    token = credentials.credentials if credentials else request.query_params.get("token")
    if not token:
        raise HTTPException(status_code=401, detail="Token tidak ada")
    user = await _resolve_user(token, db)
    await tamu.jaga(request, user, db)
    return user


async def require_verifier(user=Depends(get_current_user)):
    """Peran yang boleh memverifikasi deteksi: peneliti atau admin.

    Peran sudah ada di tabel users sejak awal, tetapi tidak pernah diperiksa.
    Tanpa ini, setiap akun yang login bisa menandai deteksi sebagai benar,
    padahal fitur itu diklaim sebagai verifikasi ahli.
    """
    from app.models.tables import UserRole

    if user.role not in (UserRole.researcher, UserRole.admin):
        raise HTTPException(
            status_code=403,
            detail="Butuh peran peneliti atau admin untuk memverifikasi deteksi.",
        )
    return user


async def require_peneliti(user=Depends(get_current_user)):
    """Peran yang boleh membaca data analitis: peneliti atau admin.

    Ranger hanya melihat rekamannya sendiri, jadi ekspor, statistik kawasan,
    daftar perangkat, dan indeks soundscape ditutup untuk ranger.
    """
    from app.models.tables import UserRole

    if user.role not in (UserRole.researcher, UserRole.admin):
        raise HTTPException(
            status_code=403,
            detail="Butuh peran peneliti atau admin untuk membuka data ini.",
        )
    return user


async def require_admin(user=Depends(get_current_user)):
    """Peran yang boleh mengubah data acuan: lokasi monitoring dan percobaan ulang job."""
    from app.models.tables import UserRole

    if user.role != UserRole.admin:
        raise HTTPException(
            status_code=403,
            detail="Butuh peran admin untuk tindakan ini.",
        )
    return user


async def user_from_token(token: str | None):
    """Resolusi token yang tidak lewat header Bearer, misalnya dari query string.

    Dipakai endpoint siaran status, karena EventSource tidak bisa mengirim header
    Authorization. Token yang tidak ada atau tidak sah dijawab 401 dari sini.
    """
    if not token:
        raise HTTPException(status_code=401, detail="Token tidak ada")
    async with async_session_factory() as db:
        user = await _resolve_user(token, db)
        await tamu.jaga(None, user, db)
        return user


async def _resolve_user(token: str, db: AsyncSession):
    from app.models.tables import User
    from app.services.security import is_token_revoked

    try:
        payload = decode_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Token tidak valid atau kedaluwarsa") from None

    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Jenis token tidak valid")

    # Logout mencatat jti di Redis. Token yang sudah dicabut ditolak walau
    # masa berlakunya belum habis.
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

    # Sesi dari sebelum sandi diganti ditolak lewat nomor versi token.
    if not token_masih_berlaku(payload, user.token_version):
        raise HTTPException(
            status_code=401,
            detail="Sesi sudah berakhir karena sandi diganti. Silakan masuk ulang.",
        )
    return user
