"""Test pengelolaan akun: admin saja, penjaga ubah peran, dan penjaga hapus."""
import uuid

import pytest
from helpers_uji import admin, login, lokasi_pertama, ranger_baru, unggah


async def _cari(client, headers, user_id: int) -> dict | None:
    daftar = await client.get("/api/v1/users", headers=headers)
    assert daftar.status_code == 200, daftar.text
    return next((u for u in daftar.json() if u["id"] == user_id), None)


@pytest.mark.anyio
async def test_users_butuh_token(client):
    assert (await client.get("/api/v1/users")).status_code == 401


@pytest.mark.anyio
async def test_users_hanya_admin(client):
    headers, user_id = await ranger_baru(client)

    lihat = await client.get("/api/v1/users", headers=headers)
    assert lihat.status_code == 403, lihat.text

    ubah = await client.patch(
        f"/api/v1/users/{user_id}/role", headers=headers, json={"role": "admin"}
    )
    assert ubah.status_code == 403, ubah.text

    hapus = await client.delete(f"/api/v1/users/{user_id}", headers=headers)
    assert hapus.status_code == 403, hapus.text


@pytest.mark.anyio
async def test_daftar_pengguna_sesuai_kontrak(client):
    headers = await admin(client)
    resp = await client.get("/api/v1/users", headers=headers)
    assert resp.status_code == 200, resp.text
    daftar = resp.json()
    assert isinstance(daftar, list) and daftar

    for user in daftar:
        assert set(user) == {
            "id", "email", "name", "role", "created_at", "is_active",
            "recording_count", "site_count", "email_terkirim",
        }
        assert user["role"] in ("ranger", "researcher", "admin")
        assert isinstance(user["recording_count"], int)
        assert isinstance(user["site_count"], int)

    admin_user = next((u for u in daftar if u["email"] == "admin@gemahutan.id"), None)
    assert admin_user is not None and admin_user["role"] == "admin"
    assert admin_user["name"] == "Admin"


@pytest.mark.anyio
async def test_admin_terakhir_tidak_bisa_diturunkan(client):
    """Admin terakhir ditolak 409, dan perannya tidak berubah setelah ditolak."""
    headers = await admin(client)
    daftar = (await client.get("/api/v1/users", headers=headers)).json()
    admin_pemilik = next(u for u in daftar if u["email"] == "admin@gemahutan.id")
    if sum(1 for u in daftar if u["role"] == "admin") != 1:
        pytest.skip("ada lebih dari satu admin di basis data, penjaga ini tidak bisa diuji")

    resp = await client.patch(
        f"/api/v1/users/{admin_pemilik['id']}/role", headers=headers, json={"role": "ranger"}
    )
    assert resp.status_code == 409, resp.text
    assert "admin terakhir" in resp.json()["detail"].lower()

    sesudah = await _cari(client, headers, admin_pemilik["id"])
    assert sesudah["role"] == "admin"


@pytest.mark.anyio
async def test_ubah_peran_diri_sendiri_ditolak(client):
    """Dengan admin lain hadir, alasan penolakannya adalah karena akun sendiri."""
    headers = await admin(client)
    daftar = (await client.get("/api/v1/users", headers=headers)).json()
    admin_pemilik = next(u for u in daftar if u["email"] == "admin@gemahutan.id")
    assert admin_pemilik["role"] == "admin"

    headers_baru, user_id = await ranger_baru(client)
    naik = await client.patch(
        f"/api/v1/users/{user_id}/role", headers=headers, json={"role": "admin"}
    )
    assert naik.status_code == 200, naik.text
    assert naik.json()["role"] == "admin"

    # Admin baru mengubah perannya sendiri: ditolak.
    sendiri = await client.patch(
        f"/api/v1/users/{user_id}/role", headers=headers_baru, json={"role": "ranger"}
    )
    assert sendiri.status_code == 409, sendiri.text
    assert "sendiri" in sendiri.json()["detail"].lower()

    # Dan akun sendiri tidak bisa dihapus.
    hapus_sendiri = await client.delete(f"/api/v1/users/{user_id}", headers=headers_baru)
    assert hapus_sendiri.status_code == 409, hapus_sendiri.text

    # Admin lain yang menurunkan perannya: berhasil.
    turun = await client.patch(
        f"/api/v1/users/{user_id}/role", headers=headers, json={"role": "ranger"}
    )
    assert turun.status_code == 200, turun.text
    assert turun.json()["role"] == "ranger"
    assert (await client.patch("/api/v1/users/999999/role", headers=headers, json={"role": "admin"})).status_code == 404


@pytest.mark.anyio
async def test_hapus_pengguna_baru_berhasil(client):
    headers = await admin(client)
    headers_baru, user_id = await ranger_baru(client)

    hapus = await client.delete(f"/api/v1/users/{user_id}", headers=headers)
    assert hapus.status_code == 204, hapus.text
    assert hapus.content == b""
    assert await _cari(client, headers, user_id) is None
    assert (await client.delete(f"/api/v1/users/{user_id}", headers=headers)).status_code == 404
    # Token akun yang sudah dihapus tidak lagi berlaku.
    assert (await client.get("/api/v1/me", headers=headers_baru)).status_code == 401


@pytest.mark.anyio
async def test_hapus_pengguna_yang_masih_punya_data_ditolak(client):
    """Akun dengan rekaman atau lokasi tidak dihapus, pesannya menyebut jumlahnya."""
    headers = await admin(client)
    site_id = await lokasi_pertama(client, headers)
    headers_ranger, user_id = await ranger_baru(client)

    rekaman = await unggah(client, headers_ranger, site_id)
    try:
        tolak = await client.delete(f"/api/v1/users/{user_id}", headers=headers)
        assert tolak.status_code == 409, tolak.text
        pesan = tolak.json()["detail"].lower()
        assert "1 rekaman" in pesan
        assert await _cari(client, headers, user_id) is not None

        # Hapus rekamannya dulu, baru akunnya bisa dihapus.
        await client.delete(f"/api/v1/recordings/{rekaman['id']}", headers=headers)
        hapus = await client.delete(f"/api/v1/users/{user_id}", headers=headers)
        assert hapus.status_code == 204, hapus.text
    finally:
        await client.delete(f"/api/v1/recordings/{rekaman['id']}", headers=headers)


@pytest.mark.anyio
async def test_nama_akun_baru_tersimpan(client):
    """Nama dari halaman daftar ikut tersimpan dan tampil di daftar pengguna."""
    email = f"fase2-nama-{uuid.uuid4().hex[:8]}@gemahutan.id"
    daftar = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "testpass123", "name": "Sari Petugas"},
    )
    assert daftar.status_code == 201, daftar.text
    user_id = daftar.json()["id"]

    headers = await admin(client)
    baris = await _cari(client, headers, user_id)
    assert baris is not None
    assert baris["name"] == "Sari Petugas"
    assert baris["is_active"] is True
    assert baris["role"] == "ranger"

    headers_baru = await login(client, email, "testpass123")
    assert (await client.get("/api/v1/me", headers=headers_baru)).status_code == 200
    await client.delete(f"/api/v1/users/{user_id}", headers=headers)
