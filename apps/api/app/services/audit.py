"""Pencatatan jejak audit.

Rancangan yang dipilih dan alasannya:

1. `catat()` menambah baris ke sesi pemanggil dan TIDAK commit sendiri. Jadi log
   dan perubahan datanya ikut satu transaksi: kalau perubahannya gagal, lognya
   ikut batal. Kalau log dicatat di transaksi terpisah, akan ada baris yang
   mengaku sebuah tindakan berhasil padahal datanya tidak berubah.

2. Kalau pencatatan gagal karena sebab teknis, tindakan utamanya TIDAK
   digagalkan. Ini pilihan sadar dengan alasan berbeda dari pembatas laju:
   menolak tindakan yang sah hanya karena tabel log bermasalah akan membuat
   aplikasi tidak bisa dipakai. Kegagalannya dicatat ke log aplikasi supaya tetap
   ada jejaknya di tempat lain.

3. Aktor disimpan sebagai email juga, bukan hanya id, supaya jejaknya tetap
   terbaca setelah akunnya dihapus.
"""
import logging

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tables import AuditLog, User

logger = logging.getLogger(__name__)

# Nama tindakan yang dikenali. Dibuat sebagai konstanta supaya salah ketik
# ketahuan saat ditulis, bukan saat membacanya setahun kemudian.
AKSI = {
    "auth.register": "Daftar akun",
    "auth.login": "Masuk",
    "auth.login_gagal": "Percobaan masuk gagal",
    "auth.logout": "Keluar",
    "auth.reset_diminta": "Minta atur ulang sandi",
    "auth.reset_selesai": "Atur ulang sandi selesai",
    "auth.aktivasi": "Aktivasi akun undangan",
    "recording.upload": "Unggah rekaman",
    "recording.delete": "Hapus rekaman",
    "detection.verify": "Verifikasi deteksi",
    "user.role_change": "Ubah peran pengguna",
    "user.undang": "Undang pengguna",
    "user.undang_ulang": "Kirim ulang undangan",
    "user.deactivate": "Nonaktifkan pengguna",
    "threshold.update": "Ubah ambang model",
}


def ip_dari_request(request: Request | None) -> str | None:
    """Ambil IP pengirim dengan cara yang sama seperti middleware pembatas laju."""
    if request is None:
        return None
    diteruskan = request.headers.get("x-forwarded-for")
    if diteruskan:
        return diteruskan.split(",")[0].strip()
    return request.client.host if request.client else None


async def catat(
    db: AsyncSession,
    action: str,
    *,
    actor: User | None = None,
    entity_type: str | None = None,
    entity_id: int | str | None = None,
    detail: dict | None = None,
    request: Request | None = None,
) -> None:
    """Tambahkan satu baris audit ke sesi pemanggil.

    Pemanggil yang bertanggung jawab melakukan commit. Kalau pemanggil rollback,
    barisnya ikut hilang, dan itu memang yang diinginkan.
    """
    baris = AuditLog(
        actor_id=getattr(actor, "id", None),
        actor_email=getattr(actor, "email", None),
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        detail=detail,
        ip=ip_dari_request(request),
    )
    try:
        db.add(baris)
    except Exception:
        logger.exception("Gagal menambahkan baris audit untuk aksi %s", action)


def label(action: str) -> str:
    """Nama tindakan yang bisa dibaca manusia, dengan cadangan nama aslinya."""
    return AKSI.get(action, action)
