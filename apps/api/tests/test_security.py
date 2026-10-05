"""Test perilaku keamanan: pembatas login, pencabutan token, pemeriksaan produksi."""
import uuid

from app.config import Settings


async def test_login_dibatasi_setelah_lima_kegagalan(client):
    """Percobaan login yang gagal berulang kali harus dikunci sementara."""
    email = f"brute-{uuid.uuid4().hex[:8]}@gemahutan.id"
    bad = {"email": email, "password": "salah-terus"}

    codes = []
    for _ in range(6):
        resp = await client.post("/api/v1/auth/login", json=bad)
        codes.append(resp.status_code)

    assert codes[:5] == [401] * 5, codes
    assert codes[5] == 429, codes

    # Percobaan berikutnya ditolak sebelum kata sandi diperiksa.
    resp = await client.post("/api/v1/auth/login", json=bad)
    assert resp.status_code == 429
    assert "Retry-After" in resp.headers


async def test_login_berhasil_menghapus_hitungan_gagal(client):
    """Setelah login benar, hitungan gagal direset sehingga tidak ada sisa blokir."""
    email = f"reset-{uuid.uuid4().hex[:8]}@gemahutan.id"
    password = "testpass123"
    await client.post("/api/v1/auth/register", json={"email": email, "password": password})

    for _ in range(3):
        assert (await client.post("/api/v1/auth/login", json={"email": email, "password": "salah"})).status_code == 401

    ok = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert ok.status_code == 200

    # Hitungan sudah bersih: tiga kegagalan lagi belum mengunci akun.
    for _ in range(3):
        resp = await client.post("/api/v1/auth/login", json={"email": email, "password": "salah"})
        assert resp.status_code == 401


async def test_logout_mencabut_access_token(client):
    """Token yang sudah logout tidak boleh dipakai lagi walau belum kedaluwarsa."""
    email = f"revoke-{uuid.uuid4().hex[:8]}@gemahutan.id"
    password = "testpass123"
    await client.post("/api/v1/auth/register", json={"email": email, "password": password})
    tokens = (
        await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    ).json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    assert (await client.get("/api/v1/me", headers=headers)).status_code == 200

    resp = await client.post(
        "/api/v1/auth/logout",
        headers=headers,
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert resp.status_code == 200
    assert resp.json()["tokens_revoked"] == 2

    assert (await client.get("/api/v1/me", headers=headers)).status_code == 401
    # Refresh token yang dicabut juga tidak bisa menukar token baru.
    assert (
        await client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    ).status_code == 401


async def test_pendaftaran_bisa_ditutup(client, monkeypatch):
    """Saat pendaftaran ditutup, /register menolak dengan 403."""
    from app.config import Settings, get_settings

    tertutup = Settings(
        allow_registration=False,
        database_url=get_settings().database_url,
        redis_url=get_settings().redis_url,
    )
    monkeypatch.setattr("app.routers.auth.get_settings", lambda: tertutup)

    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": f"baru-{uuid.uuid4().hex[:8]}@gemahutan.id", "password": "testpass123"},
    )
    assert resp.status_code == 403
    assert "Pendaftaran akun ditutup" in resp.json()["detail"]


async def test_konfigurasi_produksi_menolak_rahasia_contoh():
    """Aplikasi harus sadar konfigurasinya belum aman saat environment=production."""
    # Nilai diisi eksplisit: tanpa ini Settings membaca .env yang isinya
    # rahasia sungguhan, sehingga test tidak lagi menguji kasus bahaya.
    default = Settings(
        environment="production",
        jwt_secret="change-me-in-production",
        secret_key="change-me-in-production",
        s3_access_key="minioadmin",
        s3_secret_key="minioadmin",
        cors_origins="http://localhost:3001",
    )
    masalah = default.production_problems()
    assert any("JWT_SECRET" in m for m in masalah)
    assert any("MinIO" in m for m in masalah)

    aman = Settings(
        environment="production",
        jwt_secret="a" * 64,
        secret_key="b" * 64,
        s3_access_key="layanan-audio",
        s3_secret_key="c" * 40,
        cors_origins="https://gemahutan.example.id",
    )
    assert aman.production_problems() == []
