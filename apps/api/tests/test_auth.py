"""Test endpoint auth: register, login, refresh, logout, /me, lockout."""
import pytest


@pytest.mark.anyio
async def test_register_menolak_password_terlalu_pendek(client):
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "test-password-pendek@gemahutan.id", "password": "1"},
    )
    assert resp.status_code == 422, resp.text


@pytest.mark.anyio
async def test_register_login_refresh_me(client):
    import uuid

    unique = uuid.uuid4().hex[:8]
    email = f"test-{unique}@gemahutan.id"

    # Register mengembalikan UserResponse. Klien harus login setelahnya.
    resp = await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "testpass123",
    })
    assert resp.status_code == 201, resp.text
    user_data = resp.json()
    assert user_data["email"] == email
    assert user_data["role"] == "ranger"

    # Login untuk dapat token.
    resp = await client.post("/api/v1/auth/login", json={
        "email": email,
        "password": "testpass123",
    })
    assert resp.status_code == 200, resp.text
    tokens = resp.json()
    assert "access_token" in tokens
    assert "refresh_token" in tokens
    access = tokens["access_token"]
    refresh = tokens["refresh_token"]

    # Verifikasi token bisa dipakai.
    resp = await client.get("/api/v1/me", headers={"Authorization": f"Bearer {access}"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["email"] == email
    assert resp.json()["role"] == "ranger"

    # Login lagi dengan akun yang sama (token baru).
    resp = await client.post("/api/v1/auth/login", json={
        "email": email,
        "password": "testpass123",
    })
    assert resp.status_code == 200, resp.text
    login_tokens = resp.json()
    assert "access_token" in login_tokens
    assert "refresh_token" in login_tokens

    # Refresh token dari register (harus masih berlaku).
    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert resp.status_code == 200, resp.text
    rotated = resp.json()
    assert "access_token" in rotated
    assert rotated["refresh_token"] != refresh

    # Token lama tidak bisa dipakai lagi (rotasi).
    old_refresh = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert old_refresh.status_code == 401

    # Tanpa token: 401.
    resp = await client.get("/api/v1/me")
    assert resp.status_code in (401, 403)

    # Register ulang email sama: 409.
    resp = await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "testpass123",
    })
    assert resp.status_code == 409

    # Login salah: 401.
    resp = await client.post("/api/v1/auth/login", json={
        "email": email,
        "password": "wrongpass",
    })
    assert resp.status_code == 401

    # Logout tanpa token: tetap 200.
    resp = await client.post("/api/v1/auth/logout")
    assert resp.status_code == 200


@pytest.mark.anyio
async def test_login_terkunci_setelah_5x_gagal_dengan_ip_sama(client):
    """D06: login gagal berulang dari IP sama mengunci akun."""
    import uuid

    unique = uuid.uuid4().hex[:8]
    email = f"test-kunci-ip-{unique}@gemahutan.id"

    # Buat akun dulu.
    resp = await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "testpass123",
    })
    assert resp.status_code == 201

    # 5x gagal dengan IP yang sama.
    for _ in range(5):
        resp = await client.post("/api/v1/auth/login", json={
            "email": email,
            "password": "wrongpass",
        })
        assert resp.status_code == 401

    # Ke-6: kena lockout 429.
    resp = await client.post("/api/v1/auth/login", json={
        "email": email,
        "password": "wrongpass",
    })
    assert resp.status_code == 429, f"seharusnya 429, dapat {resp.status_code}"
    assert "Retry-After" in resp.headers


@pytest.mark.anyio
async def test_login_tidak_terkunci_dari_ip_lain_untuk_email_sama(client):
    """D06: gagal login dari IP A tidak mengunci login dari IP B."""
    import uuid

    unique = uuid.uuid4().hex[:8]
    email = f"test-kunci-ip-lain-{unique}@gemahutan.id"

    # Buat akun.
    resp = await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "testpass123",
    })
    assert resp.status_code == 201

    # 4x gagal dari "IP A" (10.0.0.1).
    for _ in range(4):
        resp = await client.post("/api/v1/auth/login",
            json={"email": email, "password": "wrongpass"},
            headers={"X-Forwarded-For": "10.0.0.1"},
        )
        assert resp.status_code == 401

    # Dari "IP B" (10.0.0.2) masih bisa login sukses.
    resp = await client.post("/api/v1/auth/login",
        json={"email": email, "password": "testpass123"},
        headers={"X-Forwarded-For": "10.0.0.2"},
    )
    assert resp.status_code == 200, (
        f"Login dari IP B seharusnya sukses, dapat {resp.status_code}: {resp.text}"
    )