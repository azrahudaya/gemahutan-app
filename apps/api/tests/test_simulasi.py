"""Simulasi perkiraan lokasi (blok K): area memuat sumber, batas masukan ditegakkan."""

import math

import pytest

from tests.helpers_uji import ranger_baru

pytestmark = pytest.mark.anyio

TIGA_ALAT = [
    {"x": -60.0, "y": -40.0, "jenis": "larik"},
    {"x": 60.0, "y": -40.0, "jenis": "larik"},
    {"x": 0.0, "y": 64.0, "jenis": "larik"},
]


async def test_tiga_alat_larik_area_memuat_sumber(client):
    """Tiga alat tanpa derau menghasilkan perkiraan dekat sumber dan area yang memuatnya."""
    headers, _ = await ranger_baru(client)
    body = {
        "alat": TIGA_ALAT,
        "sumber": [40.0, -20.0],
        "snr_db": 40.0,
        "benih": 2026,
        "sinkron": True,
    }
    r = await client.post("/api/v1/simulasi/lokasi", json=body, headers=headers)
    assert r.status_code == 200, r.text
    data = r.json()

    assert data["perkiraan"] is not None
    assert data["radius_area_m"] is not None
    assert data["galat_m"] is not None
    # Tanpa derau, arah GCC-PHAT hampir tepat, jadi galat harus kecil.
    assert data["galat_m"] < 10.0, data

    px, py = data["perkiraan"]
    sx, sy = data["sumber"]
    assert math.hypot(px - sx, py - sy) <= data["radius_area_m"], data

    # Semua alat larik harus mengembalikan arah.
    assert all(a["azimuth_deg"] is not None for a in data["arah"]), data


async def test_kurang_dari_dua_larik_tanpa_area(client):
    """Satu larik dan satu satu_kanal hanya memberi arah, tanpa area."""
    headers, _ = await ranger_baru(client)
    body = {
        "alat": [
            {"x": -60.0, "y": -40.0, "jenis": "larik"},
            {"x": 60.0, "y": -40.0, "jenis": "satu_kanal"},
        ],
        "sumber": [40.0, -20.0],
        "snr_db": 40.0,
        "benih": 1,
        "sinkron": True,
    }
    r = await client.post("/api/v1/simulasi/lokasi", json=body, headers=headers)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["perkiraan"] is None
    assert data["radius_area_m"] is None
    # Satu alat larik memberi arah, satu_kanal tidak.
    arah_larik = [a for a in data["arah"] if a["azimuth_deg"] is not None]
    assert len(arah_larik) == 1, data


async def test_simulasi_menolak_kurang_dari_dua_alat(client):
    headers, _ = await ranger_baru(client)
    body = {"alat": [{"x": 0.0, "y": 0.0}], "sumber": [10.0, 10.0]}
    r = await client.post("/api/v1/simulasi/lokasi", json=body, headers=headers)
    assert r.status_code == 400, r.text


async def test_simulasi_ditolak_tanpa_token(client):
    body = {"alat": TIGA_ALAT, "sumber": [40.0, -20.0]}
    r = await client.post("/api/v1/simulasi/lokasi", json=body)
    assert r.status_code == 401, r.text
