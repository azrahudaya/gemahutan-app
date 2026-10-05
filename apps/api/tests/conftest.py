"""Fixture bersama untuk test API.

Catatan penting: engine async di app/database.py memegang connection pool.
Kalau pool itu dipakai lintas event loop (tiap test punya loop sendiri), asyncpg
melempar InterfaceError dan healthz ikut jadi 503. Fixture autouse di bawah
menutup pool setiap test selesai, jadi setiap test mulai dari pool bersih.
"""
import uuid

import pytest
from app.database import async_engine
from app.main import app
from httpx import ASGITransport, AsyncClient


@pytest.fixture(scope="session", autouse=True)
def _bersihkan_data_uji_setelah_sesi():
    """Buang akun, lokasi, dan perangkat hasil pengujian setelah sesi selesai.

    Test berjalan di database yang sama dengan data demo, jadi tanpa langkah ini
    halaman Pengguna dan Perangkat terisi baris sampah setiap kali test jalan.
    """
    yield
    from tests.bersih_data import bersihkan

    try:
        laporan = bersihkan()
    except Exception as exc:  # noqa: BLE001 - pembersihan gagal tidak boleh menutupi hasil test
        print(f"Pembersihan data uji gagal: {exc}")
        return
    if any(v for v in laporan.values() if isinstance(v, int)):
        print(f"Data uji dibersihkan: {laporan}")


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def _matikan_pembatas_laju():
    """Matikan pembatas laju selama test.

    Test menjalankan lebih dari 200 permintaan HTTP dalam beberapa detik dari satu
    alamat, jadi pembatasnya akan memblokir test itu sendiri dan menyisakan
    kegagalan 429 yang tidak ada hubungannya dengan yang sedang diuji. Test
    pembatas laju sendiri menyalakannya kembali di dalam test-nya.
    """
    from app import middleware_limits

    semula = middleware_limits.AKTIF
    middleware_limits.AKTIF = False
    yield
    middleware_limits.AKTIF = semula


@pytest.fixture(autouse=True)
async def _dispose_engine_between_tests():
    yield
    await async_engine.dispose()


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
async def auth_headers(client) -> dict:
    """Daftar + login user unik, kembalikan header Authorization.

    Peran bawaan hasil pendaftaran adalah petugas lapangan, jadi fixture ini
    dipakai untuk menguji bahwa tindakan berperan tertentu memang ditolak.
    """
    email = f"test-{uuid.uuid4().hex[:8]}@gemahutan.id"
    await client.post("/api/v1/auth/register", json={"email": email, "password": "testpass123"})
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": "testpass123"})
    tokens = resp.json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def _login(client, email: str, password: str) -> dict:
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture
async def admin_headers(client) -> dict:
    """Akun admin hasil seed, untuk endpoint yang mengubah data acuan."""
    return await _login(client, "admin@gemahutan.id", "admin123")


@pytest.fixture
async def peneliti_headers(client) -> dict:
    """Akun peneliti hasil seed, untuk verifikasi deteksi."""
    return await _login(client, "peneliti@gemahutan.id", "peneliti123")
