"""Test object-level authorization untuk jobs, batches, exports, stats.

Sebelum patch: endpoint rentang tidak mem-filter `uploaded_by` atau scope berbasis
pemilik, sehingga ranger A dapat melihat data ranger B lewat GET jobs, exports,
batches, dan stats. Setelah patch, hanya boleh ada satu ranger yang punya akses
ke data miliknya; admin melihat semuanya; tanpa token ditolak 401.

Catatan APP_01-D: exports dan stats sekarang peneliti dan admin saja (ranger 403),
jadi object-level filtering untuk exports digantikan penjaga peran. Object-level
tetap berlaku untuk jobs dan batches.

Kasus:
1. Ranger A unggah rekaman -> ranger B GET /jobs kosong, tanpa baris A.
2. Ranger tidak bisa akses exports (403); admin bisa (200).
3. Admin GET semua -> 200.
4. Tanpa token -> 401 untuk jobs/batches/exports/stats.
"""
import io
import struct
import uuid
import wave

import pytest


def wav_senyap(detik: float = 0.4, sr: int = 8000) -> bytes:
    """WAV mono berisi keheningan, dibuat di memori untuk uji unggah."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        jumlah = int(sr * detik)
        w.writeframes(struct.pack(f"<{jumlah}h", *([0] * jumlah)))
    return buf.getvalue()


async def _login(client, email: str, password: str) -> dict:
    resp = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _daftar_ranger(client, prefix: str) -> tuple[dict, int]:
    email = f"{prefix}-{uuid.uuid4().hex[:8]}@gemahutan.id"
    daftar = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "testpass123", "name": f"Uji {prefix}"},
    )
    assert daftar.status_code == 201, daftar.text
    headers = await _login(client, email, "testpass123")
    return headers, daftar.json()["id"]


async def _unggah(client, headers: dict, site_id: int) -> dict:
    resp = await client.post(
        "/api/v1/recordings",
        headers=headers,
        files={"file": ("uji-fase3.wav", wav_senyap(), "audio/wav")},
        data={"site_id": str(site_id)},
    )
    assert resp.status_code in (201, 202), resp.text
    return resp.json()


@pytest.mark.anyio
async def test_ranger_lain_tidak_lihat_jobs_rekaman_pemilik(client):
    """Ranger B tidak boleh melihat job hasil unggahan ranger A.

    Ranger A unggah satu rekaman, ranger B meminta daftar job. Kalau query
    tidak mem-filter uploaded_by, ranger B mendapat baris job ranger A.
    """
    headers_admin = await _login(client, "admin@gemahutan.id", "admin123")
    lokasi = await client.get("/api/v1/sites", headers=headers_admin)
    assert lokasi.status_code == 200 and lokasi.json(), "butuh minimal satu lokasi"
    site_id = lokasi.json()[0]["id"]

    pemilik_a, _ = await _daftar_ranger(client, "fase3-pemilik")
    pembaca_b, _ = await _daftar_ranger(client, "fase3-pembaca")

    rekaman_a = await _unggah(client, pemilik_a, site_id)

    try:
        # Ranger A melihat job miliknya sendiri (status awal biasanya pending).
        jobs_a = await client.get(
            "/api/v1/jobs", headers=pemilik_a, params={"recording_id": rekaman_a["id"]}
        )
        assert jobs_a.status_code == 200, jobs_a.text
        assert any(j["recording_id"] == rekaman_a["id"] for j in jobs_a.json()), jobs_a.text

        # Ranger B mendapat 200 tetapi tidak ada baris yang menunjuk rekaman A.
        jobs_b = await client.get(
            "/api/v1/jobs", headers=pembaca_b, params={"recording_id": rekaman_a["id"]}
        )
        assert jobs_b.status_code == 200, jobs_b.text
        ids_b = [j["recording_id"] for j in jobs_b.json()]
        assert rekaman_a["id"] not in ids_b, jobs_b.json()
    finally:
        # Admin boleh menghapus rekaman uji.
        await client.delete(f"/api/v1/recordings/{rekaman_a['id']}", headers=headers_admin)


@pytest.mark.anyio
async def test_ranger_tidak_boleh_akses_ekspor(client):
    """Ekspor sekarang peneliti dan admin saja, ranger ditolak 403.

    Sebelum APP_01-D, ranger bisa membaca ekspor dengan filter object-level
    (hanya data miliknya). Aturan baru menutup ekspor untuk ranger seluruhnya,
    jadi object-level filtering di endpoint ini digantikan penjaga peran.
    """
    headers_admin = await _login(client, "admin@gemahutan.id", "admin123")
    pemilik_a, _ = await _daftar_ranger(client, "fase3-pemilik")

    for path in ("/api/v1/exports/recordings", "/api/v1/exports/verified"):
        ekspor = await client.get(path, headers=pemilik_a, params={"format": "json"})
        assert ekspor.status_code == 403, ekspor.text

    # Admin tetap bisa.
    for path in ("/api/v1/exports/recordings", "/api/v1/exports/verified"):
        ekspor = await client.get(path, headers=headers_admin, params={"format": "json"})
        assert ekspor.status_code == 200, ekspor.text


@pytest.mark.anyio
async def test_admin_lihat_jobs_batches_exports_stats(client):
    """Admin melihat semua endpoint rentang dengan 200, bukan 401/403."""
    headers_admin = await _login(client, "admin@gemahutan.id", "admin123")

    for path, params in (
        ("/api/v1/jobs", {"limit": 5}),
        ("/api/v1/batches", {}),
        ("/api/v1/exports/recordings", {"format": "json"}),
        ("/api/v1/exports/verified", {"format": "json"}),
        ("/api/v1/stats/overview", {}),
        ("/api/v1/stats/species", {}),
        ("/api/v1/stats/timeline", {}),
    ):
        resp = await client.get(path, headers=headers_admin, params=params)
        assert resp.status_code == 200, f"{path} -> {resp.status_code}: {resp.text}"


@pytest.mark.anyio
async def test_anonymous_ditolak_401_untuk_endpoint_rentang(client):
    """Tanpa token, endpoint rentang mengembalikan 401, bukan 200 atau 403."""
    for path in (
        "/api/v1/jobs",
        "/api/v1/batches",
        "/api/v1/batches/abc",
        "/api/v1/exports/recordings",
        "/api/v1/exports/verified",
        "/api/v1/stats/overview",
        "/api/v1/stats/species",
        "/api/v1/stats/timeline",
    ):
        resp = await client.get(path)
        assert resp.status_code == 401, f"{path} -> {resp.status_code}: {resp.text}"