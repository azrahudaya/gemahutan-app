"""Test unggah batch, status batch, progres job, dan kolom lokalisasi."""
import pytest
from helpers_uji import admin, lokasi_pertama, ranger_baru, unggah, wav_senyap


async def _unggah_batch(client, headers, site_id, nama_berkas: list[tuple[str, bytes, str]], **form):
    data = {"site_id": str(site_id), **{k: str(v) for k, v in form.items()}}
    resp = await client.post(
        "/api/v1/recordings/batch",
        headers=headers,
        files=[("files", (nama, isi, tipe)) for nama, isi, tipe in nama_berkas],
        data=data,
    )
    return resp


@pytest.mark.anyio
async def test_unggah_batch_satu_berkas_gagal_sisanya_lolos(client):
    headers = await admin(client)
    site_id = await lokasi_pertama(client, headers)

    resp = await _unggah_batch(
        client,
        headers,
        site_id,
        [
            ("satu.wav", wav_senyap(), "audio/wav"),
            ("dua.txt", b"bukan audio", "text/plain"),
            ("tiga.webm", b"\x1aE\xdf\xa3bukan-audio-sungguhan", "audio/webm"),
        ],
    )
    assert resp.status_code == 201, resp.text
    hasil = resp.json()

    assert hasil["batch_id"]
    assert hasil["count"] == 3, hasil
    assert hasil["accepted"] == 1, hasil
    assert hasil["failed"] == 2, hasil
    assert {item["filename"] for item in hasil["items"]} == {"satu.wav", "dua.txt", "tiga.webm"}

    gagal = next(item for item in hasil["items"] if item["filename"] == "dua.txt")
    assert gagal["status"] == "failed"
    assert gagal["recording_id"] is None
    assert "tidak didukung" in gagal["error"].lower()

    lolos = [item for item in hasil["items"] if item["recording_id"] is not None]
    assert len(lolos) == 1

    # Rekaman hasil batch menyimpan nama berkas asli dan id batchnya.
    satu = next(item for item in lolos if item["filename"] == "satu.wav")
    detail = await client.get(f"/api/v1/recordings/{satu['recording_id']}", headers=headers)
    assert detail.status_code == 200, detail.text
    assert detail.json()["batch_id"] == hasil["batch_id"]
    assert detail.json()["filename"] == "satu.wav"
    assert isinstance(detail.json()["progress"], int)
    assert "stage" in detail.json()

    # Bersihkan rekaman hasil batch.
    for item in lolos:
        await client.delete(f"/api/v1/recordings/{item['recording_id']}", headers=headers)


@pytest.mark.anyio
async def test_batch_batas_jumlah_berkas(client):
    headers = await admin(client)
    site_id = await lokasi_pertama(client, headers)

    banyak = await _unggah_batch(
        client,
        headers,
        site_id,
        [(f"b{i}.wav", wav_senyap(0.05), "audio/wav") for i in range(21)],
    )
    assert banyak.status_code == 400, banyak.text
    assert "20" in banyak.json()["detail"]


@pytest.mark.anyio
async def test_ranger_boleh_unggah_batch(client):
    """Unggah batch bukan tindakan admin: petugas lapangan memang yang memakainya."""
    headers_admin = await admin(client)
    site_id = await lokasi_pertama(client, headers_admin)
    headers, _ = await ranger_baru(client)

    resp = await _unggah_batch(client, headers, site_id, [("lapangan.wav", wav_senyap(), "audio/wav")])
    assert resp.status_code == 201, resp.text
    item = resp.json()["items"][0]
    assert item["recording_id"] is not None
    await client.delete(f"/api/v1/recordings/{item['recording_id']}", headers=headers_admin)


@pytest.mark.anyio
async def test_daftar_dan_detail_batch(client):
    headers = await admin(client)
    site_id = await lokasi_pertama(client, headers)

    unggahan = await _unggah_batch(
        client,
        headers,
        site_id,
        [("pagi.wav", wav_senyap(), "audio/wav"), ("siang.wav", wav_senyap(), "audio/wav")],
    )
    assert unggahan.status_code == 201, unggahan.text
    batch_id = unggahan.json()["batch_id"]
    id_rekaman = [item["recording_id"] for item in unggahan.json()["items"]]

    try:
        daftar = await client.get("/api/v1/batches", headers=headers)
        assert daftar.status_code == 200, daftar.text
        ringkas = next(b for b in daftar.json() if b["batch_id"] == batch_id)
        assert set(ringkas) == {
            "batch_id", "created_at", "total", "done", "failed", "progress_percent",
        }
        assert ringkas["total"] == 2

        # Urutan terbaru dulu: batch ini harus muncul sebelum batch yang lebih lama.
        urutan = [b["batch_id"] for b in daftar.json()]
        assert urutan.index(batch_id) == 0

        detail = await client.get(f"/api/v1/batches/{batch_id}", headers=headers)
        assert detail.status_code == 200, detail.text
        isi = detail.json()
        assert set(isi) == {
            "batch_id", "total", "done", "failed", "pending", "processing",
            "progress_percent", "recordings",
        }
        assert isi["total"] == 2
        assert isi["done"] + isi["failed"] + isi["pending"] + isi["processing"] == 2
        assert 0 <= isi["progress_percent"] <= 100
        assert {r["id"] for r in isi["recordings"]} == set(id_rekaman)
        for baris in isi["recordings"]:
            assert set(baris) == {"id", "filename", "status", "progress", "stage"}
            assert baris["filename"].endswith(".wav")
            assert 0 <= baris["progress"] <= 100

        # Batch yang tidak ada dijawab 404, bukan daftar kosong.
        assert (await client.get("/api/v1/batches/tidakada", headers=headers)).status_code == 404
    finally:
        for rid in id_rekaman:
            await client.delete(f"/api/v1/recordings/{rid}", headers=headers)


@pytest.mark.anyio
async def test_batches_butuh_token(client):
    assert (await client.get("/api/v1/batches")).status_code == 401
    assert (await client.get("/api/v1/batches/apa-saja")).status_code == 401


@pytest.mark.anyio
async def test_respons_rekaman_memuat_progres_dan_tahap(client):
    headers = await admin(client)
    site_id = await lokasi_pertama(client, headers)
    rekaman = await unggah(client, headers, site_id)
    try:
        detail = await client.get(f"/api/v1/recordings/{rekaman['id']}", headers=headers)
        assert detail.status_code == 200
        assert isinstance(detail.json()["progress"], int)
        assert 0 <= detail.json()["progress"] <= 100
        assert "stage" in detail.json()
        assert detail.json()["stage"] in (None, "antre", "unduh", "dekode", "birdnet",
                                          "klasifikasi", "lokalisasi", "indeks",
                                          "spektrogram", "selesai", "gagal")

        daftar = await client.get("/api/v1/recordings", headers=headers, params={"page_size": 5})
        assert daftar.status_code == 200
        for item in daftar.json()["items"]:
            assert isinstance(item["progress"], int)
            assert "stage" in item and "batch_id" in item
    finally:
        await client.delete(f"/api/v1/recordings/{rekaman['id']}", headers=headers)


@pytest.mark.anyio
async def test_jobs_filter_active_dan_limit(client):
    headers = await admin(client)
    site_id = await lokasi_pertama(client, headers)
    rekaman = await unggah(client, headers, site_id)
    try:
        aktif = await client.get(
            "/api/v1/jobs", headers=headers, params={"status": "active", "limit": 1}
        )
        assert aktif.status_code == 200, aktif.text
        jobs = aktif.json()
        assert len(jobs) <= 1
        for job in jobs:
            assert job["status"] in ("pending", "running")
            assert isinstance(job["progress"], int)
            assert "stage" in job

        semua = await client.get("/api/v1/jobs", headers=headers, params={"limit": 3})
        assert semua.status_code == 200
        assert len(semua.json()) <= 3

        # Nilai yang tidak dikenal tetap ditolak.
        assert (
            await client.get("/api/v1/jobs", headers=headers, params={"status": "ngawur"})
        ).status_code == 422
        assert (
            await client.get("/api/v1/jobs", headers=headers, params={"limit": 0})
        ).status_code == 422
        assert (
            await client.get("/api/v1/jobs", headers=headers, params={"limit": 5000})
        ).status_code == 422
    finally:
        await client.delete(f"/api/v1/recordings/{rekaman['id']}", headers=headers)


@pytest.mark.anyio
async def test_deteksi_memuat_kolom_lokalisasi(client):
    """Kolom lokalisasi harus ada di respons deteksi, null kalau belum dihitung."""
    headers = await admin(client)
    daftar = await client.get("/api/v1/recordings", headers=headers)
    kandidat = [r for r in daftar.json()["items"] if (r.get("detection_count") or 0) > 0]
    if not kandidat:
        pytest.skip("belum ada rekaman berisi deteksi")

    rows = await client.get(
        f"/api/v1/recordings/{kandidat[0]['id']}/detections", headers=headers
    )
    assert rows.status_code == 200, rows.text
    assert rows.json()
    for det in rows.json():
        assert set(det) >= {
            "azimuth_deg", "azimuth_confidence", "azimuth_kembar_deg",
            "range_m", "localization_engine",
        }
        # Nilai palsu nol tidak boleh dipakai untuk menandai "tidak ada".
        if det["azimuth_deg"] is None:
            assert det["azimuth_confidence"] is None
            assert det["azimuth_kembar_deg"] is None
            assert det["range_m"] is None
            assert det["localization_engine"] is None


@pytest.mark.anyio
async def test_model_info_memuat_blok_lokalisasi(client):
    headers = await admin(client)
    resp = await client.get("/api/v1/model/info", headers=headers)
    assert resp.status_code == 200, resp.text
    lok = resp.json()["localization"]
    assert set(lok) >= {
        "butuh_kanal_minimal", "butuh_geometri", "terpasang_di_worker",
        "disimpan_ke_deteksi", "batas",
    }
    assert lok["butuh_kanal_minimal"] >= 2
    assert lok["butuh_geometri"] is True
    assert isinstance(lok["terpasang_di_worker"], bool)
    assert lok["disimpan_ke_deteksi"] is True
    assert isinstance(lok["batas"], list) and len(lok["batas"]) >= 3


def test_webm_di_tipe_dan_ekstensi_yang_diizinkan():
    """Rekaman dari browser berformat webm, jadi harus ada di dua daftar sekaligus."""
    from app.routers.recordings import ALLOWED_EXTENSIONS, ALLOWED_TYPES

    # Setiap tipe MIME yang diterima harus punya ekstensi yang juga diterima.
    pasangan = {
        "audio/wav": "wav",
        "audio/x-wav": "wav",
        "audio/wave": "wav",
        "audio/mpeg": "mp3",
        "audio/mp3": "mp3",
        "audio/flac": "flac",
        "audio/x-flac": "flac",
        "audio/ogg": "ogg",
        "audio/opus": "opus",
        "audio/mp4": "m4a",
        "audio/m4a": "m4a",
        "audio/x-m4a": "m4a",
        "audio/aac": "aac",
        "audio/webm": "webm",
        "video/webm": "webm",
    }
    assert "webm" in ALLOWED_EXTENSIONS
    assert {"audio/webm", "video/webm"} <= ALLOWED_TYPES
    for tipe, ext in pasangan.items():
        assert tipe in ALLOWED_TYPES, f"tipe {tipe} hilang dari ALLOWED_TYPES"
        assert ext in ALLOWED_EXTENSIONS, f"ekstensi {ext} hilang dari ALLOWED_EXTENSIONS"
    # Tidak ada tipe MIME yang menempel ke ekstensi di luar daftar.
    assert ALLOWED_TYPES - set(pasangan) == {"application/octet-stream"}
