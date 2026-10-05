"""Akun tamu untuk halaman depan publik.

Halaman depan mengizinkan siapa saja mencoba unggah tanpa daftar. Dulu semua
pengunjung memakai satu akun demo bersama, sehingga setiap pengunjung bisa melihat,
mengekspor, bahkan menghapus rekaman pengunjung lain. Sekarang tiap pengunjung
mendapat akun tamu sendiri, dan akun tamu hanya boleh memakai jalur yang dibutuhkan
halaman depan, untuk rekaman miliknya sendiri.

Akun tamu ditandai lewat domain email, jadi tidak perlu kolom atau nilai enum baru
di basis data. Domain `.invalid` dicadangkan RFC 2606 dan tidak akan pernah menjadi
alamat sungguhan.
"""

import re
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, Request
from sqlalchemy import delete as sa_delete
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

DOMAIN_TAMU = "tamu.gemahutan.invalid"

# Jalur yang boleh dipakai akun tamu: (metode, pola path, butuh kepemilikan rekaman).
_IZIN: list[tuple[str, re.Pattern[str], bool]] = [
    ("GET", re.compile(r"^/api/v1/me$"), False),
    ("GET", re.compile(r"^/api/v1/species$"), False),
    ("GET", re.compile(r"^/api/v1/sites$"), False),
    ("GET", re.compile(r"^/api/v1/model/info$"), False),
    ("POST", re.compile(r"^/api/v1/recordings$"), False),
    ("GET", re.compile(r"^/api/v1/recordings/(\d+)(/audio|/detections|/spectrogram)?$"), True),
]


def adalah_tamu(user) -> bool:
    return bool(user and user.email and user.email.endswith("@" + DOMAIN_TAMU))


def email_tamu_baru() -> str:
    return f"tamu-{secrets.token_hex(8)}@{DOMAIN_TAMU}"


async def jaga(request: Request | None, user, db: AsyncSession) -> None:
    """Tolak permintaan akun tamu yang keluar dari daftar izin.

    Rekaman orang lain dijawab 404, bukan 403, supaya tamu tidak bisa menebak
    nomor rekaman mana yang ada. Akun tamu juga dibatasi maksimal
    `tamu_batas_unggah_per_hari` unggahan per 24 jam; lebih dari itu dijawab 429.
    """
    if not adalah_tamu(user):
        return
    if request is None:
        raise HTTPException(403, "Akun tamu tidak boleh memakai fitur ini.")

    path = request.url.path.rstrip("/") or "/"
    for metode, pola, perlu_milik in _IZIN:
        cocok = pola.match(path)
        if request.method != metode or not cocok:
            continue
        if perlu_milik:
            from app.models.tables import Recording

            pemilik = (
                await db.execute(select(Recording.uploaded_by).where(Recording.id == int(cocok.group(1))))
            ).scalar()
            if pemilik != user.id:
                raise HTTPException(404, "Rekaman tidak ditemukan")
        if metode == "POST" and path == "/api/v1/recordings":
            await _cek_kuota_unggah(user, db)
        return
    raise HTTPException(403, "Akun tamu tidak boleh memakai fitur ini.")


async def _cek_kuota_unggah(user, db: AsyncSession) -> None:
    """Tolak unggahan tamu kalau sudah melewati batas per 24 jam (429)."""
    from app.config import get_settings
    from app.models.tables import Recording
    from sqlalchemy import func

    batas = get_settings().tamu_batas_unggah_per_hari
    sejak = datetime.now(UTC) - timedelta(hours=24)
    jumlah = (
        await db.execute(
            select(func.count())
            .select_from(Recording)
            .where(Recording.uploaded_by == user.id, Recording.created_at >= sejak)
        )
    ).scalar() or 0
    if jumlah >= batas:
        raise HTTPException(
            429,
            "Batas unggahan harian tercapai. Akun tamu maksimal "
            f"{batas} rekaman per 24 jam. Coba lagi besok.",
        )


async def bersihkan(db: AsyncSession, umur_jam: int = 24) -> dict[str, int]:
    """Hapus akun tamu yang lebih tua dari `umur_jam` beserta rekaman dan audionya."""
    from app.models.tables import AcousticIndex, Detection, Job, Recording, User
    from app.services.spectrogram_cache import cache_spectrogram_key
    from app.services.storage import delete_object

    batas = datetime.now(UTC) - timedelta(hours=umur_jam)
    tamu = (
        await db.execute(
            select(User).where(User.email.like(f"%@{DOMAIN_TAMU}"), User.created_at < batas)
        )
    ).scalars().all()

    jumlah_rekaman = 0
    for user in tamu:
        rekaman = (
            await db.execute(select(Recording).where(Recording.uploaded_by == user.id))
        ).scalars().all()
        for r in rekaman:
            delete_object(r.storage_key)
            delete_object(cache_spectrogram_key(r.storage_key))
            await db.execute(sa_delete(Detection).where(Detection.recording_id == r.id))
            await db.execute(sa_delete(AcousticIndex).where(AcousticIndex.recording_id == r.id))
            await db.execute(sa_delete(Job).where(Job.recording_id == r.id))
            await db.execute(sa_delete(Recording).where(Recording.id == r.id))
            jumlah_rekaman += 1
        await db.execute(sa_delete(User).where(User.id == user.id))
    await db.commit()
    return {"akun": len(tamu), "rekaman": jumlah_rekaman}
