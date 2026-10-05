"""Uji audit tinggi: ranger tidak melihat data analitis, tetapi form rekam tetap jalan."""

from helpers_uji import ranger_baru


async def test_ranger_bisa_baca_perangkat_pilihan(client):
    """W-07: ranger boleh membaca daftar perangkat singkat untuk form rekam/unggah."""
    headers, _ = await ranger_baru(client)
    resp = await client.get("/api/v1/devices/pilihan", headers=headers)
    assert resp.status_code == 200, resp.text
    for item in resp.json():
        # Kolom teknis (serial, jarak mikrofon, jumlah rekaman) tidak bocor.
        assert "serial" not in item
        assert "mic_spacing_m" not in item
        assert "recording_count" not in item


async def test_ranger_detection_count_terbatas(client):
    """W-10: ranger baru tanpa rekaman melihat detection_count 0 di daftar spesies."""
    headers, _ = await ranger_baru(client)
    resp = await client.get("/api/v1/species", headers=headers)
    assert resp.status_code == 200, resp.text
    for item in resp.json():
        assert item.get("detection_count", 0) == 0, item
