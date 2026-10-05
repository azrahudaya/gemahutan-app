"""Test perangkat: hak akses peran, CRUD, dan penolakan hapus saat masih dipakai."""
import uuid

import pytest
from helpers_uji import admin, lokasi_pertama, ranger_baru, unggah


async def _buat_perangkat(client, headers, site_id, **tambahan) -> dict:
    body = {
        "name": f"Perangkat Uji {uuid.uuid4().hex[:6]}",
        "type": "audiomoth",
        "site_id": site_id,
        "channel_count": 4,
        "mic_spacing_m": 0.5,
        "notes": "dipasang di pohon jati",
    }
    body.update(tambahan)
    resp = await client.post("/api/v1/devices", headers=headers, json=body)
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.mark.anyio
async def test_unggah_menolak_perangkat_dari_lokasi_lain(client):
    headers = await admin(client)
    site_a = await lokasi_pertama(client, headers)
    dibuat = await client.post(
        "/api/v1/sites",
        headers=headers,
        json={"name": f"Lokasi Uji Beda {uuid.uuid4().hex[:6]}", "latitude": -6.8, "longitude": 107.5},
    )
    assert dibuat.status_code == 201, dibuat.text
    site_b = dibuat.json()["id"]
    device = await _buat_perangkat(client, headers, site_a)
    try:
        resp = await client.post(
            "/api/v1/recordings",
            headers=headers,
            files={"file": ("uji-device-site.wav", b"RIFF", "audio/wav")},
            data={"site_id": str(site_b), "device_id": str(device["id"])},
        )
        assert resp.status_code == 400, resp.text
        assert "lokasi" in resp.json()["detail"].lower()
    finally:
        await client.delete(f"/api/v1/devices/{device['id']}", headers=headers)
        await client.delete(f"/api/v1/sites/{site_b}", headers=headers)


@pytest.mark.anyio
async def test_devices_butuh_token(client):
    resp = await client.get("/api/v1/devices")
    assert resp.status_code == 401, resp.text


@pytest.mark.anyio
async def test_peran_ranger_tidak_boleh_mengakses_perangkat(client):
    """Ranger tidak bisa melihat maupun mengubah perangkat. Itu urusan admin dan peneliti."""
    headers, _ = await ranger_baru(client)
    site_id = await lokasi_pertama(client, headers)

    lihat = await client.get("/api/v1/devices", headers=headers)
    assert lihat.status_code == 403, lihat.text

    tambah = await client.post(
        "/api/v1/devices",
        headers=headers,
        json={"name": "Perangkat Ranger", "type": "phone", "site_id": site_id},
    )
    assert tambah.status_code == 403, tambah.text

    ubah = await client.patch("/api/v1/devices/1", headers=headers, json={"active": False})
    assert ubah.status_code == 403, ubah.text

    hapus = await client.delete("/api/v1/devices/1", headers=headers)
    assert hapus.status_code == 403, hapus.text


@pytest.mark.anyio
async def test_admin_crud_perangkat(client):
    headers = await admin(client)
    site_id = await lokasi_pertama(client, headers)

    # Tambah
    perangkat = await _buat_perangkat(client, headers, site_id, serial="AM-001")
    device_id = perangkat["id"]
    assert perangkat["recording_count"] == 0
    assert perangkat["active"] is True
    assert perangkat["channel_count"] == 4
    assert perangkat["mic_spacing_m"] == pytest.approx(0.5)
    assert perangkat["site_name"]
    assert set(perangkat) == {
        "id", "name", "type", "site_id", "site_name", "serial", "channel_count",
        "mic_spacing_m", "reference_distance_m", "reference_level_db",
        "installed_at", "active", "notes", "recording_count",
    }

    # Muncul di daftar, termasuk lewat filter lokasi dan status aktif.
    daftar = await client.get("/api/v1/devices", headers=headers, params={"site_id": site_id})
    assert daftar.status_code == 200
    assert any(d["id"] == device_id for d in daftar.json())
    assert all(d["site_id"] == site_id for d in daftar.json())

    # Ubah sebagian: kolom yang tidak dikirim tidak ikut berubah.
    ubah = await client.patch(
        f"/api/v1/devices/{device_id}",
        headers=headers,
        json={"channel_count": 2, "active": False, "serial": "AM-001-B"},
    )
    assert ubah.status_code == 200, ubah.text
    assert ubah.json()["channel_count"] == 2
    assert ubah.json()["active"] is False
    assert ubah.json()["name"] == perangkat["name"]
    assert ubah.json()["notes"] == "dipasang di pohon jati"

    nonaktif = await client.get("/api/v1/devices", headers=headers, params={"active": False})
    assert nonaktif.status_code == 200
    assert any(d["id"] == device_id for d in nonaktif.json())
    assert all(d["active"] is False for d in nonaktif.json())

    # Lokasi yang tidak ada ditolak.
    salah = await client.post(
        "/api/v1/devices",
        headers=headers,
        json={"name": "Perangkat Salah", "type": "phone", "site_id": 999999},
    )
    assert salah.status_code == 400, salah.text

    assert (await client.patch("/api/v1/devices/999999", headers=headers, json={"active": True})).status_code == 404

    # Hapus perangkat yang belum dipakai rekaman.
    hapus = await client.delete(f"/api/v1/devices/{device_id}", headers=headers)
    assert hapus.status_code == 204, hapus.text
    assert hapus.content == b""

    sisa = await client.get("/api/v1/devices", headers=headers, params={"site_id": site_id})
    assert all(d["id"] != device_id for d in sisa.json())
    assert (await client.delete(f"/api/v1/devices/{device_id}", headers=headers)).status_code == 404


@pytest.mark.anyio
async def test_perangkat_yang_dipakai_rekaman_tidak_bisa_dihapus(client):
    """Penghapusan ditolak 409 dan pesannya menyebut jumlah rekaman pemakainya."""
    headers = await admin(client)
    site_id = await lokasi_pertama(client, headers)
    perangkat = await _buat_perangkat(client, headers, site_id)
    device_id = perangkat["id"]

    rekaman = await unggah(client, headers, site_id, device_id)
    try:
        tolak = await client.delete(f"/api/v1/devices/{device_id}", headers=headers)
        assert tolak.status_code == 409, tolak.text
        pesan = tolak.json()["detail"].lower()
        assert "1 rekaman" in pesan and "perangkat" in pesan

        # Perangkat masih ada setelah penolakan.
        cek = await client.get("/api/v1/devices", headers=headers, params={"active": True})
        assert any(d["id"] == device_id for d in cek.json())

        # Setelah rekamannya dipindah ke perangkat lain, perangkat bisa dihapus.
        lain = await _buat_perangkat(client, headers, site_id, name=f"Perangkat Lain {uuid.uuid4().hex[:6]}")
        pindah = await client.patch(
            f"/api/v1/recordings/{rekaman['id']}", headers=headers, json={"device_id": lain["id"]}
        )
        assert pindah.status_code == 200, pindah.text

        hapus = await client.delete(f"/api/v1/devices/{device_id}", headers=headers)
        assert hapus.status_code == 204, hapus.text

        await client.delete(f"/api/v1/recordings/{rekaman['id']}", headers=headers)
        await client.delete(f"/api/v1/devices/{lain['id']}", headers=headers)
    finally:
        await client.delete(f"/api/v1/recordings/{rekaman['id']}", headers=headers)
