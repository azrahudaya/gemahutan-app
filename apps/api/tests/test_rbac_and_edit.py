"""Test peran dan operasi ubah/hapus data.

Sebelum ini tidak ada pemeriksaan peran sama sekali dan tidak ada endpoint ubah
atau hapus. Akibatnya siapa pun yang punya akun bisa menandai deteksi sebagai
terverifikasi ahli, dan rekaman salah unggah tidak bisa dibatalkan dari aplikasi.
"""
import io
import struct
import uuid
import wave

import pytest


def wav_senyap(detik: float = 1.0, sr: int = 8000) -> bytes:
    """WAV mono berisi keheningan, dibuat di memori untuk uji unggah."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        jumlah = int(sr * detik)
        w.writeframes(struct.pack(f"<{jumlah}h", *([0] * jumlah)))
    return buf.getvalue()


async def _login(client, email: str, password: str) -> dict:
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _admin(client) -> dict:
    return await _login(client, "admin@gemahutan.id", "admin123")


@pytest.mark.anyio
async def test_pengguna_lain_tidak_bisa_membaca_rekaman_dan_job(client):
    """Ranger hanya melihat rekaman yang dia unggah, bukan objek milik ranger lain."""
    headers_admin = await _admin(client)
    lokasi = await client.get("/api/v1/sites", headers=headers_admin)
    assert lokasi.status_code == 200 and lokasi.json(), "butuh minimal satu lokasi"
    site_id = lokasi.json()[0]["id"]

    email_a = f"uji-pemilik-{uuid.uuid4().hex[:8]}@gemahutan.id"
    email_b = f"uji-pembaca-{uuid.uuid4().hex[:8]}@gemahutan.id"
    for email in (email_a, email_b):
        daftar = await client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "testpass123", "name": "Uji akses"},
        )
        assert daftar.status_code == 201, daftar.text
    pemilik = await _login(client, email_a, "testpass123")
    pembaca = await _login(client, email_b, "testpass123")

    dibuat = await client.post(
        "/api/v1/recordings",
        headers=pemilik,
        files={"file": ("uji-akses.wav", wav_senyap(), "audio/wav")},
        data={"site_id": str(site_id)},
    )
    assert dibuat.status_code in (201, 202), dibuat.text
    recording_id = dibuat.json()["id"]

    assert (await client.get(f"/api/v1/recordings/{recording_id}", headers=pemilik)).status_code == 200
    assert (await client.get(f"/api/v1/recordings/{recording_id}", headers=pembaca)).status_code == 404
    assert (await client.get(f"/api/v1/recordings/{recording_id}/detections", headers=pembaca)).status_code == 404
    assert (await client.get(f"/api/v1/recordings/{recording_id}/audio", headers=pembaca)).status_code == 404

    jobs = await client.get(
        f"/api/v1/jobs?recording_id={recording_id}", headers=pembaca
    )
    assert jobs.status_code == 200 and jobs.json() == []

    exported = await client.get("/api/v1/exports/recordings?format=json", headers=pembaca)
    assert exported.status_code == 403


@pytest.mark.anyio
async def test_audio_mendukung_http_range(client):
    headers = await _admin(client)
    lokasi = await client.get("/api/v1/sites", headers=headers)
    assert lokasi.status_code == 200 and lokasi.json()
    dibuat = await client.post(
        "/api/v1/recordings",
        headers=headers,
        files={"file": ("uji-range.wav", wav_senyap(), "audio/wav")},
        data={"site_id": str(lokasi.json()[0]["id"])},
    )
    assert dibuat.status_code in (201, 202), dibuat.text
    rid = dibuat.json()["id"]
    resp = await client.get(
        f"/api/v1/recordings/{rid}/audio",
        headers={**headers, "Range": "bytes=0-9"},
    )
    assert resp.status_code == 206, resp.text
    assert resp.headers["accept-ranges"] == "bytes"
    assert resp.headers["content-range"].startswith("bytes 0-9/")
    assert len(resp.content) == 10


@pytest.mark.anyio
async def test_unggah_menolak_berkas_bukan_audio(client, auth_headers):
    sites = await client.get("/api/v1/sites", headers=auth_headers)
    assert sites.status_code == 200 and sites.json()
    resp = await client.post(
        "/api/v1/recordings",
        headers=auth_headers,
        files={"file": ("uji-bukan-audio.wav", b"not audio", "audio/wav")},
        data={"site_id": str(sites.json()[0]["id"])},
    )
    assert resp.status_code in (400, 415, 422), resp.text


@pytest.mark.anyio
async def test_ranger_tidak_menerima_detail_spasial_lokasi_global(client, auth_headers):
    resp = await client.get("/api/v1/sites", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json(), "butuh lokasi seed"
    site = resp.json()[0]
    assert site["latitude"] is None
    assert site["longitude"] is None
    assert site["recordings_count"] == 0


@pytest.mark.anyio
async def test_admin_bisa_daftarkan_lokasi(client):
    """Admin boleh menambah lokasi. Lokasinya dihapus lagi di akhir test."""
    headers = await _admin(client)
    nama = f"Lokasi Uji RBAC {uuid.uuid4().hex[:6]}"
    resp = await client.post(
        "/api/v1/sites",
        headers=headers,
        json={"name": nama, "latitude": -6.9, "longitude": 107.6},
    )
    assert resp.status_code == 201, resp.text
    site_id = resp.json()["id"]

    # Lokasi baru belum dipakai rekaman, jadi harus bisa dihapus.
    resp = await client.delete(f"/api/v1/sites/{site_id}", headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["site_id"] == site_id

    sisa = await client.get(f"/api/v1/sites/{site_id}", headers=headers)
    assert sisa.status_code == 404


@pytest.mark.anyio
async def test_peran_ranger_tidak_boleh_menambah_lokasi(client, auth_headers):
    """User biasa ditolak 403, bukan diam-diam diizinkan."""
    resp = await client.post(
        "/api/v1/sites",
        headers=auth_headers,
        json={"name": f"Lokasi Uji Ranger {uuid.uuid4().hex[:6]}", "latitude": -6.9, "longitude": 107.6},
    )
    assert resp.status_code == 403, resp.text
    assert "admin" in resp.json()["detail"].lower()


@pytest.mark.anyio
async def test_peran_ranger_tidak_boleh_memverifikasi(client, auth_headers):
    """Verifikasi ahli harus punya peran peneliti atau admin."""
    resp = await client.post(
        "/api/v1/detections/1/verify", headers=auth_headers, json={"status": "correct"}
    )
    assert resp.status_code == 403, resp.text


@pytest.mark.anyio
async def test_peran_ranger_tidak_boleh_mengulang_job(client, auth_headers):
    resp = await client.post("/api/v1/jobs/1/retry", headers=auth_headers)
    assert resp.status_code == 403, resp.text


@pytest.mark.anyio
async def test_peneliti_boleh_memverifikasi(client):
    """Akun peneliti yang di-seed boleh memverifikasi, dan hasilnya tersimpan."""
    headers = await _login(client, "peneliti@gemahutan.id", "peneliti123")
    daftar = await client.get("/api/v1/recordings", headers=headers)
    assert daftar.status_code == 200
    kandidat = [r for r in daftar.json()["items"] if (r.get("detection_count") or 0) > 0]
    if not kandidat:
        pytest.skip("belum ada rekaman berisi deteksi")

    rid = kandidat[0]["id"]
    baris = (
        await client.get(f"/api/v1/recordings/{rid}/detections", headers=headers)
    ).json()
    assert baris, "rekaman dengan detection_count > 0 harus punya baris deteksi"

    resp = await client.post(
        f"/api/v1/detections/{baris[0]['id']}/verify",
        headers=headers,
        json={"status": "correct"},
    )
    assert resp.status_code == 200, resp.text

    ulang = await client.get(f"/api/v1/recordings/{rid}/detections", headers=headers)
    terverifikasi = [d for d in ulang.json() if d["id"] == baris[0]["id"]][0]
    assert terverifikasi["verified_status"] == "correct"


@pytest.mark.anyio
async def test_unggah_ubah_hapus_rekaman_dengan_peran(client):
    """Ranger boleh unggah dan menghapus rekamannya sendiri, ranger lain tidak."""
    headers = await _admin(client)
    lokasi = await client.get("/api/v1/sites", headers=headers)
    assert lokasi.status_code == 200 and lokasi.json(), "butuh minimal satu lokasi"
    site_id = lokasi.json()[0]["id"]

    # Pemilik: user baru dengan peran bawaan.
    email_pemilik = f"uji-pemilik-{uuid.uuid4().hex[:8]}@gemahutan.id"
    await client.post(
        "/api/v1/auth/register", json={"email": email_pemilik, "password": "testpass123"}
    )
    pemilik = await _login(client, email_pemilik, "testpass123")

    unggah = await client.post(
        "/api/v1/recordings",
        headers=pemilik,
        files={"file": ("uji-senyap.wav", wav_senyap(), "audio/wav")},
        data={"site_id": str(site_id)},
    )
    assert unggah.status_code in (201, 202), unggah.text
    recording_id = unggah.json()["id"]

    # Ubah metadata: pindahkan ke lokasi yang sama, isi waktu perekaman.
    ubah = await client.patch(
        f"/api/v1/recordings/{recording_id}",
        headers=pemilik,
        json={"site_id": site_id, "recorded_at": "2026-09-20T22:30:00+00:00"},
    )
    assert ubah.status_code == 200, ubah.text
    assert ubah.json()["recorded_at"] is not None

    # Ranger lain tidak boleh menghapus rekaman ini.
    email_lain = f"uji-lain-{uuid.uuid4().hex[:8]}@gemahutan.id"
    await client.post(
        "/api/v1/auth/register", json={"email": email_lain, "password": "testpass123"}
    )
    lain = await _login(client, email_lain, "testpass123")
    tolak = await client.delete(f"/api/v1/recordings/{recording_id}", headers=lain)
    assert tolak.status_code == 403, tolak.text

    # Admin boleh menghapus, dan objeknya benar-benar hilang.
    hapus = await client.delete(f"/api/v1/recordings/{recording_id}", headers=headers)
    assert hapus.status_code == 200, hapus.text
    assert hapus.json()["recording_id"] == recording_id

    hilang = await client.get(f"/api/v1/recordings/{recording_id}", headers=headers)
    assert hilang.status_code == 404


@pytest.mark.anyio
async def test_lokasi_berisi_rekaman_tidak_bisa_dihapus(client):
    """Penghapusan lokasi yang masih dipakai ditolak dengan 409, bukan menghapus rekaman."""
    headers = await _admin(client)
    daftar = await client.get("/api/v1/sites", headers=headers)
    assert daftar.status_code == 200
    terpakai = [s for s in daftar.json() if (s.get("recordings_count") or 0) > 0]
    if not terpakai:
        pytest.skip("belum ada lokasi berisi rekaman")

    resp = await client.delete(f"/api/v1/sites/{terpakai[0]['id']}", headers=headers)
    assert resp.status_code == 409, resp.text
    assert "rekaman" in resp.json()["detail"].lower()


@pytest.mark.anyio
async def test_spektrogram_pakai_cache(client):
    """Permintaan kedua harus dilayani dari cache, bukan render ulang."""
    headers = await _admin(client)
    daftar = await client.get("/api/v1/recordings", headers=headers)
    kandidat = [r for r in daftar.json()["items"] if (r.get("detection_count") or 0) > 0]
    if not kandidat:
        pytest.skip("belum ada rekaman berisi deteksi")

    rid = kandidat[0]["id"]
    pertama = await client.get(f"/api/v1/recordings/{rid}/spectrogram", headers=headers)
    assert pertama.status_code == 200, pertama.text
    assert pertama.headers["content-type"] == "image/png"

    kedua = await client.get(f"/api/v1/recordings/{rid}/spectrogram", headers=headers)
    assert kedua.status_code == 200
    assert kedua.headers.get("x-spektrogram-cache") == "hit"
    assert kedua.content == pertama.content


@pytest.mark.anyio
async def test_ambang_di_database_sama_dengan_kalibrasi(client):
    """Halaman Spesies menampilkan ambang dari database, jadi harus sama dengan hasil kalibrasi."""
    import json
    import os
    from pathlib import Path

    def cari_thresholds() -> Path | None:
        """Cari ml/reports/thresholds.json dari beberapa tata letak.

        Di dalam image API berkasnya ada di /app/ml, di CI repo dipakai langsung
        dari root, jadi jalurnya tidak bisa dipatok dengan satu nilai.
        """
        akar = []
        if os.getenv("ML_DIR"):
            akar.append(Path(os.environ["ML_DIR"]).parent)
        akar += list(Path(__file__).resolve().parents)
        for kandidat_akar in akar:
            kandidat = kandidat_akar / "ml" / "reports" / "thresholds.json"
            if kandidat.exists():
                return kandidat
        return None

    berkas = cari_thresholds()
    if berkas is None:
        pytest.skip("thresholds.json tidak ada di image ini")
    ambang = json.loads(berkas.read_text())

    headers = await _admin(client)
    resp = await client.get("/api/v1/species", headers=headers)
    assert resp.status_code == 200
    di_db = {s["scientific_name"]: s["default_threshold"] for s in resp.json()}

    beda = [
        (nama, di_db.get(nama), nilai)
        for nama, nilai in ambang.items()
        if nama != "_negative" and nama in di_db and abs(di_db[nama] - float(nilai)) > 1e-9
    ]
    assert not beda, f"ambang berbeda antara database dan hasil kalibrasi: {beda[:5]}"
