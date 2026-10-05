#!/usr/bin/env python3
"""Peringatan disk GemaHutan.

Dijalankan cron tiap jam. Kirim email lewat SMTP Gmail (smtplib bawaan) kalau
pemakaian disk di atas ambang (default 80%). Paling banyak satu email per 6 jam;
penanda waktu disimpan di /var/lib/gemahutan/disk_terakhir.

Kredensial SMTP dibaca dari /etc/gemahutan/notif.env (SMTP_USER,
SMTP_APP_PASSWORD, NOTIF_KE). Mode 600, tidak di repo.

Pakai --uji untuk mengirim satu email percobaan tanpa memeriksa disk.
"""
from __future__ import annotations

import argparse
import os
import shutil
import smtplib
import sys
import time
from email.message import EmailMessage
from pathlib import Path

AMBANG = 80          # persen
JEDA_DETIK = 6 * 3600  # 6 jam
PENANDA = Path("/var/lib/gemahutan/disk_terakhir")
NOTIF_ENV = Path("/etc/gemahutan/notif.env")


def baca_notif() -> tuple[str, str, str]:
    """Baca SMTP_USER, SMTP_APP_PASSWORD, NOTIF_KE dari notif.env. Tanpa mencetak nilainya."""
    if not NOTIF_ENV.is_file():
        return "", "", ""
    nilai: dict[str, str] = {}
    for baris in NOTIF_ENV.read_text(encoding="utf-8").splitlines():
        if "=" not in baris or baris.lstrip().startswith("#"):
            continue
        k, v = baris.split("=", 1)
        nilai[k.strip()] = v.strip().strip('"').strip("'")
    return nilai.get("SMTP_USER", ""), nilai.get("SMTP_APP_PASSWORD", ""), nilai.get("NOTIF_KE", "")


def kirim(subjek: str, isi: str) -> bool:
    user, sandi, ke = baca_notif()
    if not (user and sandi and ke):
        print("notif.env belum lengkap; email tidak dikirim")
        return False
    pesan = EmailMessage()
    pesan["Subject"] = subjek
    pesan["From"] = user
    pesan["To"] = ke
    pesan.set_content(isi)
    try:
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as s:
            s.starttls()
            s.login(user, sandi)
            s.send_message(pesan)
    except Exception as e:  # noqa: BLE001
        print(f"gagal kirim email: {type(e).__name__}")
        return False
    return True


def pemakaian_disk() -> tuple[float, str]:
    """Kembalikan (persen, perangkat) untuk partisi root yang paling penuh."""
    terburuk: tuple[float, str] = (0.0, "")
    for p in ("/", "/var", "/opt"):
        try:
            total, dipakai, bebas = shutil.disk_usage(p)
        except OSError:
            continue
        persen = (dipakai / total) * 100.0 if total else 0.0
        if persen > terburuk[0]:
            terburuk = (persen, p)
    return terburuk


def main() -> int:
    ap = argparse.ArgumentParser(description="Peringatan disk GemaHutan")
    ap.add_argument("--uji", action="store_true", help="kirim satu email percobaan")
    args = ap.parse_args()

    if args.uji:
        ok = kirim(
            "[GemaHutan] Email uji peringatan disk",
            "Ini email percobaan dari ops/peringatan_disk.py. Kalau sampai, SMTP sudah benar.",
        )
        print("uji email:", "terkirim" if ok else "gagal (cek notif.env)")
        return 0 if ok else 1

    persen, partisi = pemakaian_disk()
    print(f"disk terpakai: {persen:.1f}% ({partisi})")
    if persen < AMBANG:
        return 0

    # Batasi frekuensi: paling banyak satu email per 6 jam.
    if PENANDA.exists():
        try:
            terakhir = float(PENANDA.read_text().strip())
        except ValueError:
            terakhir = 0.0
        if time.time() - terakhir < JEDA_DETIK:
            print(f"baru kirim email < 6 jam lalu, lewati")
            return 0

    ok = kirim(
        "[GemaHutan] Disk hampir penuh",
        f"Pemakaian disk {partisi} sudah {persen:.1f}%, melewati ambang {AMBANG}%.\n"
        f"Segera bebaskan ruang di server produksi.",
    )
    if ok:
        PENANDA.parent.mkdir(parents=True, exist_ok=True)
        PENANDA.write_text(str(time.time()))
        print("email peringatan terkirim")
    else:
        print("email peringatan gagal")
    return 0


if __name__ == "__main__":
    sys.exit(main())
