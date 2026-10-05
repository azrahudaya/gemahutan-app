"""Blok F dan G: spesies prioritas dan kerahasiaan lokasi deteksinya."""

import pytest

from app.database import async_session_factory
from app.models.tables import Detection, Recording, Species, User
from sqlalchemy import select, text

from tests.helpers_uji import admin, ranger_baru

pytestmark = pytest.mark.anyio


async def test_seed_menandai_spesies_prioritas(client):
    """Seed menandai Nisaetus bartelsi (iucn) dan Haliastur indus (permen_p106)."""
    headers = await admin(client)
    r = await client.get("/api/v1/species", headers=headers)
    assert r.status_code == 200, r.text
    daftar = {s["scientific_name"]: s for s in r.json()}

    elang_jawa = daftar.get("Nisaetus bartelsi")
    assert elang_jawa is not None, "Nisaetus bartelsi harus ada di daftar spesies"
    assert elang_jawa["prioritas"] is True
    assert elang_jawa["sumber_prioritas"] == "iucn"

    elang_bondol = daftar.get("Haliastur indus")
    assert elang_bondol is not None, "Haliastur indus harus ada di daftar spesies"
    assert elang_bondol["prioritas"] is True
    assert elang_bondol["sumber_prioritas"] == "permen_p106"

    # Spesies umum tidak ditandai prioritas.
    kutilang = daftar.get("Pycnonotus aurigaster")
    assert kutilang is not None
    assert kutilang["prioritas"] is False


async def test_admin_menandai_dan_melepas_prioritas(client):
    """Admin bisa menandai dan melepas prioritas dengan sumber 'admin'."""
    headers = await admin(client)
    daftar = (await client.get("/api/v1/species", headers=headers)).json()
    target = next(s for s in daftar if s["scientific_name"] == "Pycnonotus aurigaster")

    r = await client.patch(
        f"/api/v1/species/{target['id']}/prioritas",
        json={"prioritas": True},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    assert r.json()["prioritas"] is True
    assert r.json()["sumber_prioritas"] == "admin"

    r = await client.patch(
        f"/api/v1/species/{target['id']}/prioritas",
        json={"prioritas": False},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    assert r.json()["prioritas"] is False
    assert r.json()["sumber_prioritas"] is None


async def test_prioritas_hanya_admin(client):
    headers, _ = await ranger_baru(client)
    r = await client.patch(
        "/api/v1/species/1/prioritas", json={"prioritas": True}, headers=headers
    )
    assert r.status_code == 403, r.text


async def test_lokasi_prioritas_disamarkan_untuk_ranger(client):
    """Koordinat lokasi dengan deteksi prioritas dibulatkan untuk ranger."""
    ranger_h, ranger_id = await ranger_baru(client)

    async with async_session_factory() as db:
        # Lokasi milik ranger sendiri, supaya koordinatnya terlihat (bukan null).
        site_id = (
            await db.execute(
                text(
                    "INSERT INTO sites (name, geom, owner_id, khusus_tamu) "
                    "VALUES (:n, ST_SetSRID(ST_MakePoint(106.8456, -6.5945), 4326), :o, false) "
                    "RETURNING id"
                ),
                {"n": "Uji Prioritas", "o": ranger_id},
            )
        ).scalar()

        # Spesies prioritas + rekaman + deteksi.
        sp = (
            await db.execute(
                select(Species).where(Species.scientific_name == "Nisaetus bartelsi")
            )
        ).scalar()
        assert sp.prioritas is True

        rec = Recording(site_id=site_id, uploaded_by=ranger_id, storage_key="x", status="done")
        db.add(rec)
        await db.flush()
        db.add(Detection(recording_id=rec.id, species_id=sp.id, confidence=0.9, start_s=0.0, end_s=1.0, engine="uji", engine_version="1"))
        await db.commit()

        try:
            r = await client.get("/api/v1/sites", headers=ranger_h)
            assert r.status_code == 200, r.text
            lokasi = next((s for s in r.json() if s["id"] == site_id), None)
            assert lokasi is not None, r.json()
            assert lokasi["lokasi_disamarkan"] is True
            # Dibulatkan ke 0,1 derajat.
            assert lokasi["latitude"] == round(-6.5945, 1)
            assert lokasi["longitude"] == round(106.8456, 1)

            admin_h = await admin(client)
            r = await client.get(f"/api/v1/sites/{site_id}", headers=admin_h)
            lokasi_admin = r.json()
            assert lokasi_admin["lokasi_disamarkan"] is False
            assert abs(lokasi_admin["latitude"] - (-6.5945)) < 1e-9
        finally:
            await db.execute(text("DELETE FROM detections WHERE recording_id = :rid"), {"rid": rec.id})
            await db.execute(text("DELETE FROM recordings WHERE id = :rid"), {"rid": rec.id})
            await db.execute(text("DELETE FROM sites WHERE id = :sid"), {"sid": site_id})
            await db.commit()
