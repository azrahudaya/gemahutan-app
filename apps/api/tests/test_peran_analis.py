"""Test aturan peran untuk data analitis.

Ekspor, statistik kawasan, daftar perangkat, dan indeks soundscape hanya untuk
peneliti dan admin. Ranger menjawab 403, peneliti 200 (atau 404 saat objeknya
tidak ada, yang membuktikan penjaga perannya sudah lewat).
"""
import pytest


@pytest.mark.anyio
async def test_ekspor_hanya_peneliti_dan_admin(client, auth_headers, peneliti_headers):
    for jalur in ("/api/v1/exports/verified", "/api/v1/exports/recordings"):
        r_ranger = await client.get(jalur, headers=auth_headers)
        assert r_ranger.status_code == 403, f"{jalur} untuk ranger harus 403"

        r_peneliti = await client.get(jalur, headers=peneliti_headers)
        assert r_peneliti.status_code == 200, f"{jalur} untuk peneliti harus 200"


@pytest.mark.anyio
async def test_statistik_hanya_peneliti_dan_admin(client, auth_headers, peneliti_headers):
    for jalur in ("/api/v1/stats/overview", "/api/v1/stats/species", "/api/v1/stats/timeline"):
        r_ranger = await client.get(jalur, headers=auth_headers)
        assert r_ranger.status_code == 403, f"{jalur} untuk ranger harus 403"

        r_peneliti = await client.get(jalur, headers=peneliti_headers)
        assert r_peneliti.status_code == 200, f"{jalur} untuk peneliti harus 200"


@pytest.mark.anyio
async def test_daftar_perangkat_hanya_peneliti_dan_admin(client, auth_headers, peneliti_headers):
    r_ranger = await client.get("/api/v1/devices", headers=auth_headers)
    assert r_ranger.status_code == 403

    r_peneliti = await client.get("/api/v1/devices", headers=peneliti_headers)
    assert r_peneliti.status_code == 200


@pytest.mark.anyio
async def test_indeks_soundscape_hanya_peneliti_dan_admin(client, auth_headers, peneliti_headers):
    # Ranger ditolak sebelum rekaman dicari, jadi 403 untuk id apa pun.
    r_ranger = await client.get("/api/v1/recordings/999999/indices", headers=auth_headers)
    assert r_ranger.status_code == 403

    # Peneliti lolos penjaga peran; rekaman tidak ada jadi 404, bukan 403.
    r_peneliti = await client.get("/api/v1/recordings/999999/indices", headers=peneliti_headers)
    assert r_peneliti.status_code == 404
