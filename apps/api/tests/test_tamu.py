"""Akun tamu halaman depan: dibuat hanya oleh server web, dan terkurung pada rekamannya sendiri."""

import pytest
from app.config import get_settings
from tests.helpers_uji import admin, lokasi_pertama, ranger_baru, unggah

pytestmark = pytest.mark.anyio

RAHASIA = "rahasia-uji-tamu"


@pytest.fixture(autouse=True)
def _nyalakan_tamu():
    s = get_settings()
    semula = (s.tamu_aktif, s.tamu_rahasia)
    s.tamu_aktif, s.tamu_rahasia = True, RAHASIA
    yield
    s.tamu_aktif, s.tamu_rahasia = semula


async def _tamu(client) -> dict:
    # IP unik per panggilan supaya pembatas laju tamu tidak menumpuk 429 pada
    # IP tetap setelah banyak test dijalankan berulang.
    import uuid

    ip = f"uji-{uuid.uuid4().hex}"
    r = await client.post("/api/v1/auth/tamu", headers={"x-tamu-rahasia": RAHASIA, "x-pengunjung-ip": ip})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def test_tanpa_rahasia_seperti_tidak_ada(client):
    r = await client.post("/api/v1/auth/tamu")
    assert r.status_code == 404
    r = await client.post("/api/v1/auth/tamu", headers={"x-tamu-rahasia": "salah"})
    assert r.status_code == 404


async def test_mati_kalau_tidak_diaktifkan(client):
    get_settings().tamu_aktif = False
    r = await client.post("/api/v1/auth/tamu", headers={"x-tamu-rahasia": RAHASIA})
    assert r.status_code == 404


async def test_jalur_halaman_depan_boleh(client):
    h = await _tamu(client)
    for path in ("/api/v1/me", "/api/v1/species", "/api/v1/sites", "/api/v1/model/info"):
        r = await client.get(path, headers=h)
        assert r.status_code == 200, (path, r.status_code)


async def test_jalur_lain_ditolak(client):
    h = await _tamu(client)
    for metode, path in (
        ("GET", "/api/v1/recordings"),
        ("GET", "/api/v1/exports/recordings"),
        ("GET", "/api/v1/devices"),
        ("GET", "/api/v1/stats/overview"),
        ("GET", "/api/v1/jobs"),
        ("POST", "/api/v1/recordings/batch"),
        ("DELETE", "/api/v1/recordings/1"),
        ("PATCH", "/api/v1/recordings/1"),
    ):
        r = await client.request(metode, path, headers=h)
        assert r.status_code == 403, (metode, path, r.status_code)


async def test_tamu_hanya_melihat_rekamannya_sendiri(client):
    ranger, _ = await ranger_baru(client)
    site_id = await lokasi_pertama(client, ranger)
    milik_ranger = (await unggah(client, ranger, site_id))["id"]

    tamu_a = await _tamu(client)
    tamu_b = await _tamu(client)
    milik_a = (await unggah(client, tamu_a, site_id))["id"]

    assert (await client.get(f"/api/v1/recordings/{milik_a}", headers=tamu_a)).status_code == 200
    assert (await client.get(f"/api/v1/recordings/{milik_a}/detections", headers=tamu_a)).status_code == 200
    for nomor in (milik_a, milik_ranger):
        for akhiran in ("", "/detections", "/spectrogram", "/audio"):
            r = await client.get(f"/api/v1/recordings/{nomor}{akhiran}", headers=tamu_b)
            assert r.status_code == 404, (nomor, akhiran, r.status_code)
    assert (await client.delete(f"/api/v1/recordings/{milik_a}", headers=tamu_a)).status_code == 403


async def test_kuota_unggah_tamu(client):
    from app.config import get_settings
    from tests.helpers_uji import unggah_mentah

    h = await _tamu(client)
    site_id = await lokasi_pertama(client, h)
    batas = get_settings().tamu_batas_unggah_per_hari
    for _ in range(batas):
        r = await unggah_mentah(client, h, site_id)
        assert r.status_code in (201, 202), r.text
    # unggahan ke-(batas+1) harus 429
    r = await unggah_mentah(client, h, site_id)
    assert r.status_code == 429, r.text
    assert "24 jam" in r.json()["detail"]


async def test_pembersihan_menghapus_tamu_lama(client):
    from datetime import timedelta

    from app.database import async_session_factory
    from app.models.tables import User
    from app.services import tamu
    from sqlalchemy import select, update

    h = await _tamu(client)
    me = (await client.get("/api/v1/me", headers=h)).json()
    async with async_session_factory() as db:
        await db.execute(update(User).where(User.id == me["id"]).values(created_at=User.created_at - timedelta(days=2)))
        await db.commit()
        hasil = await tamu.bersihkan(db, umur_jam=24)
        assert hasil["akun"] >= 1
        sisa = (await db.execute(select(User).where(User.id == me["id"]))).scalar()
        assert sisa is None


async def test_tamu_hanya_melihat_lokasi_khusus_tamu(client):
    """W-01: akun tamu hanya melihat lokasi sistem "Uji coba publik".

    Peran petugas (di sini admin) tidak melihat lokasi khusus tamu di daftar.
    """
    h_tamu = await _tamu(client)
    h_admin = await admin(client)

    lokasi_tamu = (await client.get("/api/v1/sites", headers=h_tamu)).json()
    assert len(lokasi_tamu) == 1, lokasi_tamu
    assert lokasi_tamu[0]["name"] == "Uji coba publik", lokasi_tamu

    lokasi_admin = (await client.get("/api/v1/sites", headers=h_admin)).json()
    nama_admin = [s["name"] for s in lokasi_admin]
    assert "Uji coba publik" not in nama_admin, nama_admin

    # Akses langsung ke id lokasi tamu oleh admin menjawab 404 (tersembunyi).
    id_tamu = lokasi_tamu[0]["id"]
    assert (await client.get(f"/api/v1/sites/{id_tamu}", headers=h_admin)).status_code == 404


async def test_rekaman_tamu_tidak_masuk_data_kawasan(client):
    """W-02: rekaman akun tamu tidak terhitung di data kawasan admin.

    Setelah tamu mengunggah rekaman, jumlah rekaman di stats/overview admin
    tidak bertambah, dan rekaman itu tidak muncul di daftar rekaman maupun
    ekspor terverifikasi admin.
    """
    h_admin = await admin(client)
    h_tamu = await _tamu(client)
    lokasi_tamu = (await client.get("/api/v1/sites", headers=h_tamu)).json()
    assert lokasi_tamu, "lokasi khusus tamu belum ada; jalankan app.seed dulu"
    site_id = lokasi_tamu[0]["id"]

    sebelum = (await client.get("/api/v1/stats/overview", headers=h_admin)).json()
    rek = await unggah(client, h_tamu, site_id)
    sesudah = (await client.get("/api/v1/stats/overview", headers=h_admin)).json()

    assert sesudah["recordings"] == sebelum["recordings"], (sebelum, sesudah)

    daftar = (
        await client.get("/api/v1/recordings", headers=h_admin, params={"page_size": 100})
    ).json()
    ids_rekaman = [r["id"] for r in daftar["items"]]
    assert rek["id"] not in ids_rekaman, ids_rekaman

    ekspor = (
        await client.get(
            "/api/v1/exports/verified", headers=h_admin, params={"format": "json", "status": "all"}
        )
    ).json()
    ids_ekspor = [d["recording_id"] for d in ekspor]
    assert rek["id"] not in ids_ekspor, ids_ekspor
