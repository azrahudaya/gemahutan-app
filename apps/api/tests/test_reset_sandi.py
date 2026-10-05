"""Test alur lupa sandi dan atur ulang sandi.

Cara mengambil token di test: token mentahnya sengaja TIDAK bisa dibaca dari basis
data, karena yang disimpan hanya hash SHA-256-nya. Itu memang sifat yang diinginkan.
Jadi test ini membuat token lewat layanannya langsung untuk kasus yang butuh token
sah, dan menguji endpoint `/forgot-password` secara terpisah untuk memastikan
barisnya benar-benar dibuat.

Semua email memakai uuid supaya suite ini bisa dijalankan berulang.
"""
import uuid

import pytest
from app.database import async_engine
from app.models.tables import PasswordResetToken, User
from app.services import password_reset
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker
from tests.conftest import _login

SANDI_AWAL = "Kicau9Hutan"
SANDI_BARU = "Merpati7Biru"

PESAN_SAMA = (
    "Kalau alamat email itu terdaftar, tautan atur ulang sandi sudah "
    "dikirim. Periksa kotak masuk dan folder spam."
)


@pytest.fixture
async def sesi_db():
    maker = async_sessionmaker(async_engine, expire_on_commit=False)
    async with maker() as s:
        yield s


async def _buat_akun(client, sesi_db) -> tuple[str, User]:
    email = f"reset-{uuid.uuid4().hex[:10]}@uji-audit.id"
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": SANDI_AWAL, "name": "Uji Reset"},
    )
    assert r.status_code == 201, r.text
    user = (await sesi_db.execute(select(User).where(User.email == email))).scalar()
    return email, user


async def _token_manual(sesi_db, user: User) -> str:
    """Buat token lewat layanannya, kembalikan token mentahnya."""
    mentah, _ = await password_reset.buat_token(sesi_db, user)
    await sesi_db.commit()
    return mentah


@pytest.mark.anyio
async def test_jawaban_tidak_membocorkan_alamat_terdaftar(client, sesi_db) -> None:
    """Jawaban untuk alamat terdaftar dan tidak terdaftar harus identik.

    Kalau berbeda, endpoint ini berubah jadi alat untuk memeriksa email mana yang
    punya akun di sistem ini.
    """
    email, _ = await _buat_akun(client, sesi_db)

    r_ada = await client.post("/api/v1/auth/forgot-password", json={"email": email})
    r_tidak = await client.post(
        "/api/v1/auth/forgot-password",
        json={"email": f"tidak-ada-{uuid.uuid4().hex[:8]}@uji-audit.id"},
    )

    assert r_ada.status_code == r_tidak.status_code == 202
    assert r_ada.json() == r_tidak.json()
    assert r_ada.json()["message"] == PESAN_SAMA


@pytest.mark.anyio
async def test_permintaan_membuat_baris_token_tanpa_menyimpan_token_mentah(
    client, sesi_db
) -> None:
    email, user = await _buat_akun(client, sesi_db)
    r = await client.post("/api/v1/auth/forgot-password", json={"email": email})
    assert r.status_code == 202

    # Disaring per pengguna. Versi pertama test ini mengambil semua baris, sehingga
    # ikut membaca sisa test lain yang tokennya sudah dipakai, dan gagal karena
    # sebab yang tidak ada hubungannya.
    baris = (
        await sesi_db.execute(
            select(PasswordResetToken).where(PasswordResetToken.user_id == user.id)
        )
    ).scalars().all()
    assert len(baris) == 1
    b = baris[0]
    # Hash SHA-256 heksadesimal, bukan token mentah.
    assert len(b.token_hash) == 64
    assert b.used_at is None
    assert b.requested_ip is not None


@pytest.mark.anyio
async def test_sandi_diganti_dan_sandi_lama_tidak_berlaku(client, sesi_db) -> None:
    email, user = await _buat_akun(client, sesi_db)
    mentah = await _token_manual(sesi_db, user)

    r = await client.post(
        "/api/v1/auth/reset-password", json={"token": mentah, "password": SANDI_BARU}
    )
    assert r.status_code == 200, r.text
    assert r.json()["sessions_revoked"] is True

    # Sandi baru berlaku, sandi lama tidak.
    await _login(client, email, SANDI_BARU)
    r_lama = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": SANDI_AWAL}
    )
    assert r_lama.status_code == 401


@pytest.mark.anyio
async def test_token_hanya_bisa_dipakai_sekali(client, sesi_db) -> None:
    _, user = await _buat_akun(client, sesi_db)
    mentah = await _token_manual(sesi_db, user)

    pertama = await client.post(
        "/api/v1/auth/reset-password", json={"token": mentah, "password": SANDI_BARU}
    )
    assert pertama.status_code == 200

    kedua = await client.post(
        "/api/v1/auth/reset-password", json={"token": mentah, "password": "Kenari8Hijau"}
    )
    assert kedua.status_code == 400
    # Pesannya harus sama dengan token yang tidak dikenal, supaya penebak tidak
    # bisa membedakan token yang pernah ada dari yang tidak.
    ketiga = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": "token-palsu-yang-cukup-panjang", "password": SANDI_BARU},
    )
    assert ketiga.status_code == 400
    assert kedua.json()["detail"] == ketiga.json()["detail"]


@pytest.mark.anyio
async def test_sandi_ganti_memutus_sesi_lama(client, sesi_db) -> None:
    """Setelah sandi diganti, token yang lama harus berhenti bekerja.

    Tanpa ini, pengaturan ulang sandi tidak mengusir siapa pun yang sudah masuk
    dengan sandi lama, sehingga pemulihannya tidak benar-benar memulihkan apa pun.
    """
    email, user = await _buat_akun(client, sesi_db)
    headers_lama = await _login(client, email, SANDI_AWAL)

    # Token lama masih bekerja sebelum sandi diganti.
    assert (await client.get("/api/v1/me", headers=headers_lama)).status_code == 200

    mentah = await _token_manual(sesi_db, user)
    r = await client.post(
        "/api/v1/auth/reset-password", json={"token": mentah, "password": SANDI_BARU}
    )
    assert r.status_code == 200

    sesudah = await client.get("/api/v1/me", headers=headers_lama)
    assert sesudah.status_code == 401
    assert "sandi diganti" in sesudah.json()["detail"].lower()

    # Token baru hasil login ulang tetap bekerja.
    headers_baru = await _login(client, email, SANDI_BARU)
    assert (await client.get("/api/v1/me", headers=headers_baru)).status_code == 200


@pytest.mark.anyio
async def test_permintaan_baru_membatalkan_token_lama(client, sesi_db) -> None:
    """Tautan lama tidak boleh tetap berlaku setelah ada permintaan baru.

    Tanpa ini, setiap tautan yang pernah dikirim tetap aktif sampai kedaluwarsa,
    sehingga kotak masuk lama jadi kumpulan kunci yang masih berfungsi.
    """
    _, user = await _buat_akun(client, sesi_db)
    lama = await _token_manual(sesi_db, user)
    baru = await _token_manual(sesi_db, user)

    r_lama = await client.post(
        "/api/v1/auth/reset-password", json={"token": lama, "password": SANDI_BARU}
    )
    assert r_lama.status_code == 400

    r_baru = await client.post(
        "/api/v1/auth/reset-password", json={"token": baru, "password": SANDI_BARU}
    )
    assert r_baru.status_code == 200


@pytest.mark.anyio
async def test_sandi_lemah_ditolak_di_jalur_pemulihan(client, sesi_db) -> None:
    """Kebijakan sandi berlaku juga di jalur pemulihan.

    Tanpa ini, sandi lemah bisa masuk lewat lupa sandi walau sudah diblokir di
    pendaftaran.
    """
    _, user = await _buat_akun(client, sesi_db)
    mentah = await _token_manual(sesi_db, user)

    r = await client.post(
        "/api/v1/auth/reset-password", json={"token": mentah, "password": "password123"}
    )
    assert r.status_code == 422


@pytest.mark.anyio
async def test_token_kedaluwarsa_ditolak(client, sesi_db) -> None:
    from datetime import UTC, datetime, timedelta

    _, user = await _buat_akun(client, sesi_db)
    mentah = await _token_manual(sesi_db, user)

    # Mundurkan masa berlakunya supaya kedaluwarsa tanpa menunggu.
    baris = (
        await sesi_db.execute(
            select(PasswordResetToken).where(PasswordResetToken.user_id == user.id)
        )
    ).scalars().first()
    baris.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    await sesi_db.commit()

    r = await client.post(
        "/api/v1/auth/reset-password", json={"token": mentah, "password": SANDI_BARU}
    )
    assert r.status_code == 400


@pytest.mark.anyio
async def test_hapus_pengguna_yang_punya_token_reset_tetap_berhasil(
    client, sesi_db
) -> None:
    """Penghapusan pengguna tidak boleh terhalang baris token atur ulang.

    Ini bug nyata yang ketemu saat mengerjakan fitur ini: kunci asing tanpa
    ON DELETE membuat penghapusan pengguna gagal. Token atur ulang itu sementara,
    jadi barisnya memang harus ikut terhapus, berbeda dari baris audit yang harus
    bertahan.
    """
    email, user = await _buat_akun(client, sesi_db)
    await client.post("/api/v1/auth/forgot-password", json={"email": email})

    sisa = (
        await sesi_db.execute(
            select(PasswordResetToken).where(PasswordResetToken.user_id == user.id)
        )
    ).scalars().all()
    assert sisa, "token atur ulang seharusnya sudah dibuat"

    headers_admin = await _login(client, "admin@gemahutan.id", "admin123")
    # Akun ini baru daftar dan tidak punya rekaman, lokasi, atau verifikasi,
    # jadi penghapusannya tidak ditahan syarat milik data.
    r = await client.delete(f"/api/v1/users/{user.id}", headers=headers_admin)
    assert r.status_code == 204, r.text

    # Baris tokennya ikut hilang, bukan tertinggal sebagai yatim.
    tersisa = (
        await sesi_db.execute(
            select(PasswordResetToken).where(PasswordResetToken.user_id == user.id)
        )
    ).scalars().all()
    assert tersisa == []
