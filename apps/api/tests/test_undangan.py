"""Test undangan akun oleh admin dan aktivasi lewat email.

Token undangan tidak bisa dibaca dari basis data (yang disimpan hanya hash-nya),
sama seperti token atur ulang sandi. Jadi test ini membuat token lewat layanannya
langsung untuk kasus yang butuh token sah, dan menguji endpoint undang secara
terpisah untuk memastikan akun nonaktif dan baris tokennya benar-benar dibuat.
"""
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from app.database import async_engine
from app.models.tables import PasswordResetToken, User
from app.services import password_reset
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker
from tests.conftest import _login

SANDI_UNDANG = "Undang9Hutan"


@pytest.fixture
async def sesi_db():
    maker = async_sessionmaker(async_engine, expire_on_commit=False)
    async with maker() as s:
        yield s


async def _undang(client, headers_admin, sesi_db, role: str = "ranger") -> User:
    email = f"uji-undang-{uuid.uuid4().hex[:10]}@uji-audit.id"
    r = await client.post(
        "/api/v1/users/undang",
        json={"email": email, "name": "Uji Undang", "role": role},
        headers=headers_admin,
    )
    assert r.status_code == 201, r.text
    assert r.json()["is_active"] is False
    user = (await sesi_db.execute(select(User).where(User.email == email))).scalar()
    return user


async def _token_undangan(sesi_db, user: User) -> str:
    mentah, _ = await password_reset.buat_token(
        sesi_db, user, masa_berlaku=timedelta(hours=72)
    )
    await sesi_db.commit()
    return mentah


@pytest.mark.anyio
async def test_undang_membuat_akun_nonaktif_dan_baris_token(client, admin_headers, sesi_db):
    user = await _undang(client, admin_headers, sesi_db)
    assert user.is_active is False
    assert user.role.value == "ranger"

    baris = (
        await sesi_db.execute(
            select(PasswordResetToken).where(PasswordResetToken.user_id == user.id)
        )
    ).scalars().all()
    assert len(baris) == 1
    assert baris[0].used_at is None
    assert baris[0].expires_at > datetime.now(UTC) + timedelta(hours=60)


@pytest.mark.anyio
async def test_undang_email_ganda_ditolak(client, admin_headers, sesi_db):
    email = f"uji-undang-{uuid.uuid4().hex[:10]}@uji-audit.id"
    body = {"email": email, "name": "Uji", "role": "ranger"}
    pertama = await client.post("/api/v1/users/undang", json=body, headers=admin_headers)
    assert pertama.status_code == 201

    kedua = await client.post("/api/v1/users/undang", json=body, headers=admin_headers)
    assert kedua.status_code == 409


@pytest.mark.anyio
async def test_undang_hanya_admin(client, auth_headers):
    r = await client.post(
        "/api/v1/users/undang",
        json={"email": f"uji-undang-{uuid.uuid4().hex[:8]}@uji-audit.id", "role": "ranger"},
        headers=auth_headers,
    )
    assert r.status_code == 403


@pytest.mark.anyio
async def test_aktivasi_mengaktifkan_akun_dan_sandi_berlaku(client, admin_headers, sesi_db):
    user = await _undang(client, admin_headers, sesi_db)
    mentah = await _token_undangan(sesi_db, user)

    r = await client.post(
        "/api/v1/auth/aktivasi", json={"token": mentah, "password": SANDI_UNDANG}
    )
    assert r.status_code == 200, r.text

    # Akun jadi aktif dan bisa login dengan sandi baru.
    await sesi_db.refresh(user)
    assert user.is_active is True
    await _login(client, user.email, SANDI_UNDANG)


@pytest.mark.anyio
async def test_aktivasi_token_salah_ditolak(client, admin_headers, sesi_db):
    await _undang(client, admin_headers, sesi_db)
    r = await client.post(
        "/api/v1/auth/aktivasi",
        json={"token": "token-palsu-yang-cukup-panjang", "password": SANDI_UNDANG},
    )
    assert r.status_code == 400


@pytest.mark.anyio
async def test_aktivasi_token_kedaluwarsa_ditolak(client, admin_headers, sesi_db):
    user = await _undang(client, admin_headers, sesi_db)
    mentah = await _token_undangan(sesi_db, user)

    baris = (
        await sesi_db.execute(
            select(PasswordResetToken).where(
                PasswordResetToken.user_id == user.id,
                PasswordResetToken.used_at.is_(None),
            )
        )
    ).scalars().first()
    baris.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    await sesi_db.commit()

    r = await client.post(
        "/api/v1/auth/aktivasi", json={"token": mentah, "password": SANDI_UNDANG}
    )
    assert r.status_code == 400


@pytest.mark.anyio
async def test_undang_ulang_untuk_akun_aktif_ditolak(client, admin_headers, sesi_db):
    user = await _undang(client, admin_headers, sesi_db)
    mentah = await _token_undangan(sesi_db, user)
    await client.post("/api/v1/auth/aktivasi", json={"token": mentah, "password": SANDI_UNDANG})

    r = await client.post(f"/api/v1/users/{user.id}/undang-ulang", headers=admin_headers)
    assert r.status_code == 409


@pytest.mark.anyio
async def test_daftar_pengguna_tidak_menampilkan_akun_tamu(client, admin_headers, sesi_db):
    # Buat akun tamu langsung di basis data, lalu pastikan tidak muncul di daftar.
    sesi_db.add(
        User(
            email=f"tamu-{uuid.uuid4().hex[:8]}@tamu.gemahutan.invalid",
            password_hash="x",
            name="Tamu",
            is_active=True,
        )
    )
    await sesi_db.commit()

    r = await client.get("/api/v1/users", headers=admin_headers)
    assert r.status_code == 200
    email_tamu = [u["email"] for u in r.json()]
    assert all(not e.endswith("@tamu.gemahutan.invalid") for e in email_tamu)


@pytest.mark.anyio
async def test_undang_email_gagal_melaporkan_email_terkirim_false(client, admin_headers):
    """W-05: kalau surel gagal terkirim, respons memuat email_terkirim: false.

    Dengan mode produksi dan SMTP kosong, endpoint undang tetap membuat akun
    (201) tetapi harus jujur memberi tahu bahwa email tidak terkirim.
    """
    from app.config import get_settings

    s = get_settings()
    semula = (s.environment, s.smtp_host, s.smtp_from)
    s.environment = "production"
    s.smtp_host = ""
    s.smtp_from = ""
    try:
        email = f"uji-undang-{uuid.uuid4().hex[:10]}@uji-audit.id"
        r = await client.post(
            "/api/v1/users/undang",
            json={"email": email, "name": "Uji Surel", "role": "ranger"},
            headers=admin_headers,
        )
        assert r.status_code == 201, r.text
        assert r.json()["email_terkirim"] is False, r.text
    finally:
        s.environment, s.smtp_host, s.smtp_from = semula
