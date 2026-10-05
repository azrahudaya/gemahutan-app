"""Test pembatas laju umum.

Pembatas ini dimatikan otomatis oleh fixture autouse di conftest supaya test lain
tidak saling memblokir. Test di sini menyalakannya kembali sementara, memakai
jatah yang sangat kecil supaya bisa ditembus dalam beberapa permintaan, lalu
mengembalikannya seperti semula.

Kunci Redis dibersihkan sebelum dan sesudah tiap test karena jendela waktunya
tetap: tanpa pembersihan, test berikutnya bisa mewarisi hitungan test sebelumnya.
"""
import pytest
from app import middleware_limits
from app.main import app
from httpx import ASGITransport, AsyncClient

PREFIX = middleware_limits.PREFIX


async def _bersihkan() -> None:
    try:
        klien = middleware_limits.PembatasLaju(app)._redis()
        kunci = await klien.keys(f"{PREFIX}*")
        # Kunci penguncian login ikut dibersihkan. Test lain di suite ini sengaja
        # memicu penguncian itu, dan jendelanya 60 detik, jadi tanpa pembersihan
        # test di sini bisa menerima 429 dari penguncian login, bukan dari
        # pembatas laju yang sedang diuji.
        kunci += await klien.keys("gemahutan:login:*")
        if kunci:
            await klien.delete(*kunci)
    except Exception:  # noqa: BLE001 - Redis tidak ada = lewati test ini, bukan gagalkan
        # Redis tidak tersedia: test pembatas laju dilewati, bukan gagal.
        pytest.skip("Redis tidak tersedia untuk test pembatas laju")


@pytest.fixture
async def klien_pembatas():
    """Klien HTTP dengan pembatas laju dinyalakan dan jatah diperkecil."""
    semula_aktif = middleware_limits.AKTIF
    semula_anggaran = dict(middleware_limits.ANGGARAN)
    middleware_limits.AKTIF = True
    middleware_limits.ANGGARAN["baca"] = (3, 60)
    middleware_limits.ANGGARAN["tulis"] = (2, 60)
    await _bersihkan()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    await _bersihkan()
    middleware_limits.AKTIF = semula_aktif
    middleware_limits.ANGGARAN.clear()
    middleware_limits.ANGGARAN.update(semula_anggaran)


@pytest.mark.anyio
async def test_permintaan_baca_dibatasi(klien_pembatas) -> None:
    # Tiga permintaan pertama lolos. Endpoint /api/v1/species butuh token, jadi
    # jawabannya 401, dan yang penting di sini bukan kodenya melainkan bahwa
    # permintaan itu sampai ke aplikasi.
    for i in range(3):
        r = await klien_pembatas.get("/api/v1/species")
        assert r.status_code != 429, f"permintaan ke-{i + 1} sudah dibatasi"

    r = await klien_pembatas.get("/api/v1/species")
    assert r.status_code == 429
    assert "retry-after" in r.headers
    badan = r.json()
    assert badan["kelas"] == "baca"
    assert badan["batas"] == 3


@pytest.mark.anyio
async def test_permintaan_tulis_punya_jatah_terpisah(klien_pembatas) -> None:
    """Jatah baca dan tulis tidak boleh saling mengurangi.

    Yang diperiksa adalah pembatas laju TIDAK menolak, bukan kode jawabannya.
    Login punya penguncian sendiri yang juga menjawab 429, jadi menuntut kode
    selain 429 akan gagal karena sebab yang tidak berhubungan.
    """
    for _ in range(3):
        await klien_pembatas.get("/api/v1/species")

    # Jatah baca sudah habis, tapi tulis harus masih penuh.
    r = await klien_pembatas.post("/api/v1/auth/login", json={"email": "a@b.id", "password": "x"})
    assert "operasi tulis" not in r.text, "jatah tulis ikut terpakai oleh permintaan baca"


@pytest.mark.anyio
async def test_healthz_tidak_pernah_dibatasi(klien_pembatas) -> None:
    """Pemeriksa kesehatan tidak boleh dihitung.

    Docker dan Caddy memanggilnya terus-menerus. Kalau dibatasi, kontainer akan
    ditandai tidak sehat padahal aplikasinya baik-baik saja.
    """
    for _ in range(12):
        r = await klien_pembatas.get("/healthz")
        assert r.status_code != 429


@pytest.mark.anyio
async def test_login_tidak_dihitung_dua_kali(klien_pembatas) -> None:
    """Login punya penguncian sendiri, jadi tidak dihitung pembatas umum.

    Kalau dihitung di dua tempat, pengguna bisa terkunci oleh dua mekanisme
    dengan pesan berbeda untuk satu sebab yang sama.
    """
    for _ in range(6):
        r = await klien_pembatas.post(
            "/api/v1/auth/login", json={"email": "a@b.id", "password": "x"}
        )
        assert r.status_code in (401, 429)
        # 429 dari penguncian login punya pesan berbeda, bukan pesan pembatas umum.
        if r.status_code == 429:
            assert "operasi tulis" not in r.text
