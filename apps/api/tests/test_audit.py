"""Test jejak audit.

Yang diuji bukan hanya barisnya bertambah, tapi juga dua sifat yang membuat jejak
ini berguna: pelakunya benar-benar tercatat, dan hanya admin yang bisa membaca.

Catatan: kode jawaban `login` gagal sengaja dibiarkan 401 walau baris auditnya
disimpan lebih dulu. Kalau pencatatan gagal dan itu sampai mengubah kode jawaban,
penyerang bisa memakai kegagalan tabel log untuk menebak akun mana yang ada.
"""
import uuid

import pytest
from app.database import async_engine
from app.models.tables import AuditLog
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker
from tests.conftest import _login


@pytest.fixture
async def sesi_db():
    """Sesi database langsung, untuk membaca tabel audit tanpa lewat API."""
    maker = async_sessionmaker(async_engine, expire_on_commit=False)
    async with maker() as s:
        yield s


@pytest.fixture(autouse=True)
async def _bersihkan_audit():
    """Buang baris audit milik test ini saja, supaya data nyata tidak terhapus."""
    yield
    maker = async_sessionmaker(async_engine, expire_on_commit=False)
    async with maker() as s:
        await s.execute(delete(AuditLog).where(AuditLog.actor_email.like("%@uji-audit.id")))
        await s.execute(delete(AuditLog).where(AuditLog.detail["email_dicoba"].astext.like("%@uji-audit.id")))
        await s.commit()


async def _ambil_audit(sesi_db, action: str, email: str | None = None):
    q = select(AuditLog).where(AuditLog.action == action)
    if email:
        q = q.where(AuditLog.actor_email == email)
    return (await sesi_db.execute(q.order_by(AuditLog.id.desc()))).scalars().all()


@pytest.mark.anyio
async def test_daftar_akun_meninggalkan_jejak(client, sesi_db) -> None:
    email = f"daftar-{uuid.uuid4().hex[:8]}@uji-audit.id"
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Kicau9Hutan", "name": "Uji Audit"},
    )
    assert r.status_code == 201

    baris = await _ambil_audit(sesi_db, "auth.register", email)
    assert len(baris) == 1
    b = baris[0]
    assert b.actor_id == r.json()["id"]
    assert b.entity_type == "user"
    assert b.entity_type and b.entity_id == str(r.json()["id"])
    assert b.detail["role"] == "ranger"


@pytest.mark.anyio
async def test_masuk_yang_berhasil_dan_yang_gagal_tercatat_beda(client, sesi_db) -> None:
    email = f"masuk-{uuid.uuid4().hex[:8]}@uji-audit.id"
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Kicau9Hutan", "name": "Uji Audit"},
    )

    gagal = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "sandi-salah-9"}
    )
    assert gagal.status_code == 401

    berhasil = await _login(client, email, "Kicau9Hutan")
    assert "Authorization" in berhasil

    # Kegagalan disimpan tanpa pelaku, dan memuat email yang dicoba supaya
    # percobaan terhadap akun yang tidak ada pun tetap terlihat. Akun yang
    # disasar tetap tercatat sebagai entity, bukan sebagai pelaku: sandi yang
    # salah tidak membuktikan pemilik akun yang mengetiknya.
    baris_gagal = await _ambil_audit(sesi_db, "auth.login_gagal")
    cocok = [b for b in baris_gagal if b.detail and b.detail.get("email_dicoba") == email]
    assert len(cocok) == 1
    assert cocok[0].actor_id is None
    assert cocok[0].actor_email is None
    assert cocok[0].entity_type == "user"
    assert cocok[0].entity_id is not None
    assert cocok[0].detail["ada_akun"] is True
    assert cocok[0].ip is not None

    baris_masuk = await _ambil_audit(sesi_db, "auth.login", email)
    assert len(baris_masuk) == 1
    assert baris_masuk[0].actor_email == email


@pytest.mark.anyio
async def test_bukan_admin_tidak_bisa_membaca_audit(client, auth_headers) -> None:
    """Peran bawaan hasil pendaftaran tidak boleh membaca jejak audit.

    Jejak ini memuat alamat IP dan riwayat tindakan tiap akun, jadi kalau semua
    peran bisa membacanya, isinya bisa dipakai memantau rekan kerja.
    """
    r = await client.get("/api/v1/audit", headers=auth_headers)
    assert r.status_code == 403


@pytest.mark.anyio
async def test_tanpa_token_ditolak(client) -> None:
    r = await client.get("/api/v1/audit")
    assert r.status_code == 401


@pytest.mark.anyio
async def test_admin_bisa_membaca_dan_menyaring(client, sesi_db) -> None:
    email = f"baca-{uuid.uuid4().hex[:8]}@uji-audit.id"
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Kicau9Hutan", "name": "Uji Audit"},
    )
    headers = await _login(client, "admin@gemahutan.id", "admin123")

    r = await client.get("/api/v1/audit", headers=headers, params={"batas": 5})
    assert r.status_code == 200
    isi = r.json()
    assert isi["total"] >= 1
    assert len(isi["items"]) <= 5
    # Daftar tindakan ikut dikirim supaya pemanggil tidak menebak namanya.
    assert "auth.register" in isi["actions"]

    # Urutan terbaru lebih dulu.
    waktu = [b["created_at"] for b in isi["items"]]
    assert waktu == sorted(waktu, reverse=True)

    # Penyaring per tindakan.
    r2 = await client.get(
        "/api/v1/audit", headers=headers, params={"aksi": "auth.register", "batas": 200}
    )
    assert r2.status_code == 200
    assert all(b["action"] == "auth.register" for b in r2.json()["items"])


@pytest.mark.anyio
async def test_batas_maksimum_ditegakkan(client) -> None:
    """Permintaan dengan batas di luar rentang ditolak, bukan dilayani diam-diam."""
    headers = await _login(client, "admin@gemahutan.id", "admin123")
    r = await client.get("/api/v1/audit", headers=headers, params={"batas": 5000})
    assert r.status_code == 422
