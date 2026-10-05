"""Token atur ulang sandi: pembuatan, pemeriksaan, dan pemakaian.

Tiga sifat yang membuat ini aman, dan masing-masing punya alasan:

1. Yang disimpan hash SHA-256 dari token, bukan tokennya. Kalau isi tabel bocor,
   token mentahnya tidak bisa dipakai membajak akun.

2. Permintaan baru membatalkan token lama yang belum dipakai. Tanpa ini, setiap
   tautan yang pernah dikirim tetap berlaku sampai kedaluwarsa, sehingga kotak
   masuk lama menjadi kumpulan kunci yang masih berfungsi.

3. Token hanya bisa dipakai sekali, ditandai `used_at` bukan dihapus, supaya
   jejaknya masih bisa ditelusuri.
"""
import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.tables import PasswordResetToken, User

# 32 byte acak dari sumber kriptografis, cukup panjang sehingga tidak bisa ditebak.
PANJANG_TOKEN_BYTE = 32


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


async def batalkan_token_lama(db: AsyncSession, user_id: int) -> int:
    """Tandai semua token aktif milik pengguna sebagai sudah dipakai.

    Dipakai dua kali: saat token baru dibuat, dan saat sandi berhasil diubah
    (supaya token lain yang belum dipakai tidak tertinggal aktif).
    """
    hasil = await db.execute(
        select(PasswordResetToken).where(
            PasswordResetToken.user_id == user_id,
            PasswordResetToken.used_at.is_(None),
        )
    )
    baris = hasil.scalars().all()
    sekarang = datetime.now(UTC)
    for b in baris:
        b.used_at = sekarang
    return len(baris)


async def buat_token(
    db: AsyncSession,
    user: User,
    ip: str | None = None,
    masa_berlaku: timedelta | None = None,
) -> tuple[str, datetime]:
    """Buat token baru, kembalikan (token_mentah, kedaluwarsa).

    Token mentah HANYA ada di nilai kembalian dan di email. Yang tersimpan di
    basis data hanya hash-nya. `masa_berlaku` dipakai undangan (72 jam); kalau
    kosong, dipakai `reset_token_minutes` dari setelan.
    """
    settings = get_settings()
    await batalkan_token_lama(db, user.id)

    if masa_berlaku is None:
        masa_berlaku = timedelta(minutes=settings.reset_token_minutes)
    mentah = secrets.token_urlsafe(PANJANG_TOKEN_BYTE)
    kedaluwarsa = datetime.now(UTC) + masa_berlaku
    db.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=_hash(mentah),
            expires_at=kedaluwarsa,
            requested_ip=ip,
        )
    )
    return mentah, kedaluwarsa


async def cari_token_valid(db: AsyncSession, mentah: str) -> PasswordResetToken | None:
    """Kembalikan baris token kalau ada, belum dipakai, dan belum kedaluwarsa."""
    if not mentah:
        return None
    hasil = await db.execute(
        select(PasswordResetToken).where(PasswordResetToken.token_hash == _hash(mentah))
    )
    baris = hasil.scalar()
    if not baris:
        return None
    if baris.used_at is not None:
        return None
    # Dibandingkan di Python, bukan di SQL, supaya perilakunya sama pada SQLite
    # dan Postgres dan tidak bergantung pada zona waktu basis data.
    kedaluwarsa = baris.expires_at
    if kedaluwarsa.tzinfo is None:
        kedaluwarsa = kedaluwarsa.replace(tzinfo=UTC)
    if kedaluwarsa <= datetime.now(UTC):
        return None
    return baris


def tautan_reset(mentah: str) -> str:
    dasar = get_settings().frontend_url.rstrip("/")
    return f"{dasar}/reset-sandi?token={mentah}"


def tautan_undangan(mentah: str) -> str:
    dasar = get_settings().frontend_url.rstrip("/")
    return f"{dasar}/atur-sandi?token={mentah}"
