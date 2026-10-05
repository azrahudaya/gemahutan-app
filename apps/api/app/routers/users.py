"""Pengelolaan akun: daftar, ubah peran, hapus. Semua hanya untuk admin.

Tidak ada satu pun endpoint di sini sebelum Fase 2, jadi peran hanya bisa diubah
lewat SQL dan akun yang salah daftar tidak bisa dibersihkan dari aplikasi.
"""
import logging
import secrets
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import delete as sa_delete
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.deps import get_db, require_admin
from app.models.tables import Detection, Recording, Site, User, UserRole
from app.schemas.user import InviteUserRequest, RoleUpdate, UserListResponse
from app.services import audit, mailer, password_reset
from app.services.auth import hash_password
from app.services.tamu import DOMAIN_TAMU

router = APIRouter(prefix="/api/v1/users", tags=["users"])

logger = logging.getLogger(__name__)


def _to_response(user: User, recording_count: int, site_count: int) -> UserListResponse:
    return UserListResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role.value,
        created_at=user.created_at.isoformat(),
        is_active=user.is_active,
        recording_count=recording_count,
        site_count=site_count,
    )


async def _hitung_milik(db: AsyncSession, user_id: int) -> tuple[int, int]:
    rekaman = (
        await db.execute(
            select(func.count(Recording.id)).where(Recording.uploaded_by == user_id)
        )
    ).scalar() or 0
    lokasi = (
        await db.execute(select(func.count(Site.id)).where(Site.owner_id == user_id))
    ).scalar() or 0
    return int(rekaman), int(lokasi)


async def _ambil(db: AsyncSession, user_id: int) -> UserListResponse:
    user = (await db.execute(select(User).where(User.id == user_id))).scalar()
    if not user:
        raise HTTPException(404, "Pengguna tidak ditemukan")
    rekaman, lokasi = await _hitung_milik(db, user_id)
    return _to_response(user, rekaman, lokasi)


@router.get("", response_model=list[UserListResponse])
async def list_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    result = await db.execute(
        select(
            User,
            func.count(Recording.id.distinct()).label("recording_count"),
            func.count(Site.id.distinct()).label("site_count"),
        )
        .outerjoin(Recording, Recording.uploaded_by == User.id)
        .outerjoin(Site, Site.owner_id == User.id)
        .where(User.email.not_like(f"%@{DOMAIN_TAMU}"))
        .group_by(User.id)
        .order_by(User.id)
    )
    return [
        _to_response(row[0], row.recording_count or 0, row.site_count or 0)
        for row in result.all()
    ]


async def _kirim_undangan(db: AsyncSession, user: User, request: Request) -> bool:
    """Buat token undangan (72 jam) dan kirim emailnya. Tanpa commit."""
    settings = get_settings()
    mentah, kedaluwarsa = await password_reset.buat_token(
        db,
        user,
        audit.ip_dari_request(request),
        timedelta(hours=settings.invite_token_hours),
    )
    terkirim = await mailer.kirim_undangan(
        user.email,
        password_reset.tautan_undangan(mentah),
        settings.invite_token_hours,
        user.name,
    )
    return terkirim


@router.post("/undang", response_model=UserListResponse, status_code=201)
async def undang_user(
    body: InviteUserRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Undang petugas baru. Akun dibuat nonaktif, diaktifkan lewat email.

    Sandinya belum ada sampai yang diundang membuka tautan dan membuatnya
    sendiri, jadi tidak ada sandi sementara yang bisa bocor lewat email.
    """
    existing = (await db.execute(select(User).where(User.email == body.email))).scalar()
    if existing:
        raise HTTPException(409, "Email sudah terdaftar.")

    user = User(
        email=body.email,
        password_hash=hash_password(secrets.token_urlsafe(32)),
        name=(body.name or "").strip()[:255] or None,
        role=body.role,
        is_active=False,
    )
    db.add(user)
    await db.flush()

    terkirim = await _kirim_undangan(db, user, request)
    await audit.catat(
        db,
        "user.undang",
        actor=current_user,
        entity_type="user",
        entity_id=user.id,
        detail={"role": body.role.value, "email_terkirim": terkirim},
        request=request,
    )
    await db.commit()
    if not terkirim:
        logger.error("Undangan untuk %s tidak terkirim", user.email)
    resp = await _ambil(db, user.id)
    resp.email_terkirim = terkirim
    return resp


@router.post("/{user_id}/undang-ulang", response_model=UserListResponse)
async def undang_ulang(
    user_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Kirim ulang undangan untuk akun yang masih menunggu aktivasi."""
    user = (await db.execute(select(User).where(User.id == user_id))).scalar()
    if not user:
        raise HTTPException(404, "Pengguna tidak ditemukan")
    if user.is_active:
        raise HTTPException(409, "Akun sudah aktif, tidak perlu undangan ulang.")

    terkirim = await _kirim_undangan(db, user, request)
    await audit.catat(
        db,
        "user.undang_ulang",
        actor=current_user,
        entity_type="user",
        entity_id=user.id,
        detail={"email_terkirim": terkirim},
        request=request,
    )
    await db.commit()
    if not terkirim:
        logger.error("Undangan ulang untuk %s tidak terkirim", user.email)
    resp = await _ambil(db, user.id)
    resp.email_terkirim = terkirim
    return resp


@router.patch("/{user_id}/role", response_model=UserListResponse)
async def update_user_role(
    user_id: int,
    body: RoleUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Ubah peran akun, dengan dua penjaga.

    Admin terakhir tidak boleh diturunkan supaya tidak ada lagi yang bisa
    mengelola lokasi, perangkat, dan akun; itu diperiksa lebih dulu supaya
    pesannya jelas. Setelah itu peran diri sendiri ditolak karena admin tidak
    boleh menutup akses dirinya di tengah pekerjaan.
    """
    user = (await db.execute(select(User).where(User.id == user_id))).scalar()
    if not user:
        raise HTTPException(404, "Pengguna tidak ditemukan")

    if user.role == UserRole.admin and body.role != UserRole.admin:
        jumlah_admin = (
            await db.execute(
                select(func.count(User.id)).where(User.role == UserRole.admin)
            )
        ).scalar() or 0
        if jumlah_admin <= 1:
            raise HTTPException(
                409,
                "Ini admin terakhir. Angkat admin lain dulu sebelum menurunkan perannya.",
            )

    if user_id == current_user.id:
        raise HTTPException(
            409, "Peran akun sendiri tidak bisa diubah dari halaman ini."
        )

    peran_lama = user.role.value
    user.role = body.role
    await audit.catat(
        db,
        "user.role_change",
        actor=current_user,
        entity_type="user",
        entity_id=user.id,
        detail={"peran_lama": peran_lama, "peran_baru": body.role.value},
        request=request,
    )
    await db.commit()
    return await _ambil(db, user_id)


@router.delete("/{user_id}", status_code=204)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Hapus akun. Ditolak untuk diri sendiri dan untuk akun yang masih punya data.

    Deteksi yang sudah diverifikasi ikut dihitung karena baris itu menyimpan
    siapa yang memverifikasi, dan jejak itu tidak boleh hilang diam-diam.
    """
    if user_id == current_user.id:
        raise HTTPException(409, "Akun sendiri tidak bisa dihapus.")

    user = (await db.execute(select(User).where(User.id == user_id))).scalar()
    if not user:
        raise HTTPException(404, "Pengguna tidak ditemukan")

    rekaman, lokasi = await _hitung_milik(db, user_id)
    verifikasi = (
        await db.execute(
            select(func.count(Detection.id)).where(Detection.verified_by == user_id)
        )
    ).scalar() or 0

    if rekaman or lokasi or verifikasi:
        bagian = []
        if rekaman:
            bagian.append(f"{rekaman} rekaman")
        if lokasi:
            bagian.append(f"{lokasi} lokasi")
        if verifikasi:
            bagian.append(f"{verifikasi} deteksi terverifikasi")
        raise HTTPException(
            409,
            "Akun ini masih terhubung ke "
            + " dan ".join(bagian)
            + ". Pindahkan atau hapus datanya dulu, lalu hapus akunnya.",
        )

    await db.execute(sa_delete(User).where(User.id == user_id))
    await db.commit()
