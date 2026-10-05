"""Pengiriman email, khususnya tautan atur ulang sandi.

Keadaan yang harus dihadapi dengan jujur: aplikasi ini belum punya server email.
Jadi modul ini sengaja dibikin punya tiga perilaku yang berbeda dan tidak
berpura-pura:

1. SMTP dikonfigurasi: email benar-benar dikirim.
2. SMTP tidak dikonfigurasi dan ini BUKAN produksi: tautannya ditulis ke log
   aplikasi supaya pengembangan bisa jalan tanpa server email.
3. SMTP tidak dikonfigurasi dan ini produksi: pengiriman dilaporkan GAGAL, dan
   kesalahannya ditulis ke log. Tidak ada tautan yang bocor ke log produksi, dan
   tidak ada klaim palsu bahwa email terkirim.

Memakai pustaka standar `smtplib` di dalam thread, bukan menambah dependensi
async baru. Pengiriman email jarang dan lambat, jadi memblokir satu thread
terpisah tidak masalah.
"""
import asyncio
import logging
import smtplib
from email.message import EmailMessage

from app.config import get_settings

logger = logging.getLogger(__name__)


def terkonfigurasi() -> bool:
    """True kalau setelan SMTP cukup untuk mengirim."""
    s = get_settings()
    return bool(s.smtp_host and s.smtp_from)


def _kirim_sinkron(tujuan: str, subjek: str, isi: str) -> None:
    s = get_settings()
    pesan = EmailMessage()
    pesan["From"] = s.smtp_from
    pesan["To"] = tujuan
    pesan["Subject"] = subjek
    pesan.set_content(isi)

    with smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=15) as smtp:
        if s.smtp_starttls:
            smtp.starttls()
        if s.smtp_user:
            smtp.login(s.smtp_user, s.smtp_password)
        smtp.send_message(pesan)


async def kirim(tujuan: str, subjek: str, isi: str) -> bool:
    """Kirim satu email. Kembalikan True kalau benar-benar terkirim.

    Pemanggil TIDAK boleh memakai nilai kembalian ini untuk memberi tahu pengguna
    apakah alamat emailnya terdaftar atau tidak. Nilainya hanya untuk log.
    """
    s = get_settings()

    if terkonfigurasi():
        try:
            await asyncio.to_thread(_kirim_sinkron, tujuan, subjek, isi)
            return True
        except Exception:
            logger.exception("Gagal mengirim email ke %s", tujuan)
            return False

    if s.environment.strip().lower() in {"production", "prod"}:
        logger.error(
            "Permintaan kirim email ke %s tetapi SMTP belum dikonfigurasi. "
            "Isi SMTP_HOST dan SMTP_FROM supaya pemulihan sandi bisa dipakai.",
            tujuan,
        )
        return False

    logger.warning("SMTP belum dikonfigurasi, isi email untuk %s:\n%s\n%s", tujuan, subjek, isi)
    return True


async def kirim_tautan_reset(tujuan: str, tautan: str, berlaku_menit: int) -> bool:
    isi = (
        "Seseorang meminta pengaturan ulang sandi untuk akun GemaHutan ini.\n\n"
        f"Buka tautan berikut untuk membuat sandi baru:\n\n{tautan}\n\n"
        f"Tautan ini berlaku {berlaku_menit} menit dan hanya bisa dipakai sekali.\n\n"
        "Kalau kamu tidak memintanya, abaikan email ini. Sandimu tidak berubah "
        "sampai tautan di atas dibuka."
    )
    return await kirim(tujuan, "Atur ulang sandi GemaHutan", isi)


async def kirim_undangan(tujuan: str, tautan: str, berlaku_jam: int, nama: str | None) -> bool:
    sapaan = f" {nama}" if nama else ""
    isi = (
        f"Halo{sapaan},\n\n"
        "Kamu diundang menjadi petugas di GemaHutan, sistem pemantauan satwa "
        "hutan lewat suara.\n\n"
        "Buka tautan berikut untuk membuat kata sandi dan mengaktifkan akunmu:\n\n"
        f"{tautan}\n\n"
        f"Tautan ini berlaku {berlaku_jam} jam dan hanya bisa dipakai sekali.\n\n"
        "Kalau kamu tidak merasa diundang, abaikan email ini."
    )
    return await kirim(tujuan, "Undangan akun GemaHutan", isi)
