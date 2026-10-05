"""Test regresi kebijakan kekuatan sandi pada pendaftaran akun.

Sebelum ini satu-satunya syarat sandi adalah panjang minimal 8 karakter, jadi
sandi seperti "password123" atau "gemahutan" diterima. Aturan sekarang menambah
syarat ragam karakter, daftar sandi umum, dan larangan memuat bagian email.

Email yang dipakai di sini sengaja dipilih supaya tidak bertabrakan dengan
"testpass123" yang dipakai test lain.
"""
import uuid

import pytest
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)

# Sandi yang harus ditolak, dengan alasan di komentar.
SANDI_DITOLAK = [
    ("pendek1", "kurang dari 8 karakter"),
    ("password123", "ada di daftar sandi umum"),
    ("gemahutan1", "ada di daftar sandi umum"),
    ("abcdefghij", "tidak memuat angka"),
    ("12345678901", "tidak memuat huruf"),
    ("budi12345678", "memuat bagian email pendaftar"),
]

SANDI_DITERIMA = ["Kicau9Hutan", "Rahasia9Kuat", "biru7langit"]


@pytest.mark.parametrize("sandi,alasan", SANDI_DITOLAK)
def test_sandi_lemah_ditolak(sandi: str, alasan: str) -> None:
    r = client.post(
        "/api/v1/auth/register",
        json={"email": "budi@gemahutan.id", "password": sandi, "name": "Budi"},
    )
    assert r.status_code == 422, f"{sandi} seharusnya ditolak karena {alasan}"


@pytest.mark.parametrize("sandi", SANDI_DITERIMA)
def test_sandi_kuat_diterima(sandi: str) -> None:
    # Email wajib unik tiap jalan. Versi pertama test ini memakai email tetap,
    # jadi jalan kedua selalu gagal dengan 409 dan tampak seperti aturan sandinya
    # yang salah, padahal akunnya cuma sudah ada.
    email = f"uji-{uuid.uuid4().hex[:10]}@gemahutan.id"
    r = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": sandi, "name": "Uji"},
    )
    assert r.status_code == 201, f"{sandi} seharusnya diterima, dapat {r.status_code}"


def test_login_sandi_salah_tetap_401_bukan_422() -> None:
    """Kebijakan sandi hanya berlaku saat daftar, bukan saat login.

    Kalau aturannya ikut dipasang di skema login, pengguna lama yang sandinya
    belum memenuhi syarat baru tidak akan pernah bisa masuk.
    """
    r = client.post(
        "/api/v1/auth/login",
        json={"email": "tidak-ada@gemahutan.id", "password": "testpass123"},
    )
    assert r.status_code == 401
