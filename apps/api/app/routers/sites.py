"""Sites router: list, detail, create.

Koordinat disimpan sebagai geometry(Point,4326). Ekstraksi lat/lon memakai
SQL text dengan cast eksplisit ke geometry supaya tidak bergantung pada
penanganan cache key SQLAlchemy untuk ekspresi fungsi PostGIS.
"""
from datetime import UTC

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_user, get_db, require_admin
from app.models.tables import User, UserRole
from app.schemas.site import SiteCreate, SiteResponse, SiteUpdate
from app.services.access import can_review_all, site_ids_prioritas
from app.services.tamu import adalah_tamu

router = APIRouter(prefix="/api/v1/sites", tags=["sites"])

# Satu lokasi dianggap aktif kalau ada rekaman dalam 180 hari terakhir.
_ACTIVE_WINDOW_DAYS = 180

# Predikat SQL untuk mengecualikan rekaman akun tamu dari agregat per lokasi.
# Data unggahan "Coba contoh" tidak boleh masuk hitungan data kawasan.
_BUKAN_TAMU_SQL = (
    "r.uploaded_by NOT IN (SELECT id FROM users WHERE email LIKE '%@tamu.gemahutan.invalid')"
)

_SITE_SELECT = f"""
    SELECT
        s.id,
        s.owner_id,
        s.name,
        s.habitat_type,
        s.location,
        s.elevation_m,
        s.description,
        s.notes,
        ST_Y(s.geom::geometry) AS latitude,
        ST_X(s.geom::geometry) AS longitude,
        s.created_at,
        (SELECT count(*) FROM recordings r WHERE r.site_id = s.id AND {_BUKAN_TAMU_SQL}) AS recordings_count,
        (SELECT count(*) FROM detections d
            JOIN recordings r ON d.recording_id = r.id
            WHERE r.site_id = s.id AND {_BUKAN_TAMU_SQL}) AS detections_count,
        (SELECT count(DISTINCT d.species_id) FROM detections d
            JOIN recordings r ON d.recording_id = r.id
            WHERE r.site_id = s.id AND {_BUKAN_TAMU_SQL}) AS species_count,
        (SELECT max(r.created_at) FROM recordings r
            WHERE r.site_id = s.id AND {_BUKAN_TAMU_SQL}) AS last_recording_at
    FROM sites s
"""


def _filter_khusus_tamu(current_user: User) -> str:
    """Klausa WHERE penyaring lokasi khusus tamu.

    Akun tamu hanya melihat lokasi sistem untuk "Coba contoh". Peran petugas
    (admin, peneliti, ranger) tidak melihatnya sama sekali.
    """
    if adalah_tamu(current_user):
        return "s.khusus_tamu = true"
    return "s.khusus_tamu = false"


def _row_to_site(row, current_user: User, sites_prioritas: set[int] | None = None) -> SiteResponse:
    last = row.last_recording_at
    is_active = last is not None and (row.recordings_count or 0) > 0
    if is_active:
        from datetime import datetime, timedelta
        is_active = last >= datetime.now(UTC) - timedelta(days=_ACTIVE_WINDOW_DAYS)

    # Ranger boleh memilih lokasi monitoring bersama saat upload, tetapi tidak
    # boleh melihat koordinat, catatan, atau agregat rekaman milik lokasi yang
    # bukan miliknya. Admin dan peneliti tetap melihat data organisasi penuh.
    detail_terbatas = current_user.role == UserRole.ranger and row.owner_id != current_user.id

    # Kerahasiaan lokasi spesies prioritas: lokasi yang punya deteksi spesies
    # prioritas koordinatnya dibulatkan untuk semua peran selain admin/peneliti.
    disamarkan = (
        not detail_terbatas
        and sites_prioritas is not None
        and row.id in sites_prioritas
        and not can_review_all(current_user)
    )
    lat = row.latitude
    lon = row.longitude
    if detail_terbatas:
        lat = lon = None
    elif disamarkan:
        lat = round(row.latitude, 1) if row.latitude is not None else None
        lon = round(row.longitude, 1) if row.longitude is not None else None

    return SiteResponse(
        id=row.id,
        name=row.name,
        latitude=lat,
        longitude=lon,
        location=None if detail_terbatas else row.location,
        habitat_type=None if detail_terbatas else row.habitat_type,
        elevation_m=None if detail_terbatas else row.elevation_m,
        description=None if detail_terbatas else row.description,
        notes=None if detail_terbatas else row.notes,
        status="active" if is_active else "inactive",
        recordings_count=0 if detail_terbatas else row.recordings_count or 0,
        detections_count=0 if detail_terbatas else row.detections_count or 0,
        species_count=0 if detail_terbatas else row.species_count or 0,
        last_recording_at=None if detail_terbatas else last.isoformat() if last else None,
        created_at=row.created_at.isoformat() if row.created_at else None,
        lokasi_disamarkan=disamarkan,
    )


@router.get("", response_model=list[SiteResponse])
async def list_sites(
    name: str | None = Query(None, max_length=255),
    location: str | None = Query(None, max_length=255),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    params = {}
    filters = [f"({_filter_khusus_tamu(current_user)})"]
    if name:
        filters.append("s.name ILIKE :name")
        params["name"] = f"%{name}%"
    if location:
        filters.append("s.location ILIKE :location")
        params["location"] = f"%{location}%"
    where = f" WHERE {' AND '.join(filters)}"

    result = await db.execute(text(_SITE_SELECT + where + " ORDER BY s.name"), params)
    prioritas = await site_ids_prioritas(db) if not can_review_all(current_user) else None
    return [_row_to_site(r, current_user, prioritas) for r in result.all()]


@router.get("/{site_id}", response_model=SiteResponse)
async def get_site(
    site_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        text(_SITE_SELECT + f" WHERE s.id = :id AND {_filter_khusus_tamu(current_user)}"),
        {"id": site_id},
    )
    row = result.first()
    if not row:
        raise HTTPException(404, "Site not found")
    prioritas = await site_ids_prioritas(db) if not can_review_all(current_user) else None
    return _row_to_site(row, current_user, prioritas)


@router.patch("/{site_id}", response_model=SiteResponse)
async def update_site(
    site_id: int,
    body: SiteUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Koreksi data lokasi. Nama yang salah sebelumnya tidak bisa diperbaiki."""
    ada = (await db.execute(text("SELECT id FROM sites WHERE id = :id"), {"id": site_id})).first()
    if not ada:
        raise HTTPException(404, "Site not found")

    set_clauses = []
    params: dict = {"id": site_id}

    if body.name is not None:
        name = body.name.strip()
        if not name:
            raise HTTPException(400, "Nama lokasi wajib diisi")
        duplikat = await db.execute(
            text("SELECT id FROM sites WHERE lower(name) = lower(:name) AND id <> :id"),
            {"name": name, "id": site_id},
        )
        if duplikat.first():
            raise HTTPException(409, f"Lokasi dengan nama '{name}' sudah ada")
        set_clauses.append("name = :name")
        params["name"] = name

    if (body.latitude is None) != (body.longitude is None):
        raise HTTPException(400, "Latitude dan longitude harus diisi bersamaan")
    if body.latitude is not None and body.longitude is not None:
        set_clauses.append("geom = ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326)")
        params["latitude"] = body.latitude
        params["longitude"] = body.longitude

    for kolom in ("location", "habitat_type", "elevation_m", "description", "notes"):
        nilai = getattr(body, kolom)
        if nilai is not None:
            set_clauses.append(f"{kolom} = :{kolom}")
            params[kolom] = nilai

    if not set_clauses:
        raise HTTPException(400, "Tidak ada kolom yang diubah")

    await db.execute(
        text(f"UPDATE sites SET {', '.join(set_clauses)} WHERE id = :id"), params
    )
    await db.commit()

    updated = await db.execute(text(_SITE_SELECT + " WHERE s.id = :id"), {"id": site_id})
    return _row_to_site(updated.first(), current_user)

@router.post("", response_model=SiteResponse, status_code=201)
async def create_site(
    body: SiteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    name = body.name.strip()
    if not name:
        raise HTTPException(400, "Nama lokasi wajib diisi")

    duplicate = await db.execute(
        text("SELECT id FROM sites WHERE lower(name) = lower(:name)"), {"name": name}
    )
    if duplicate.first():
        raise HTTPException(409, f"Lokasi dengan nama '{name}' sudah ada")

    if (body.latitude is None) != (body.longitude is None):
        raise HTTPException(400, "Latitude dan longitude harus diisi bersamaan")

    geom_sql = "NULL"
    params = {
        "name": name,
        "habitat_type": body.habitat_type,
        "location": body.location,
        "elevation_m": body.elevation_m,
        "description": body.description,
        "notes": body.notes,
        "owner_id": current_user.id,
    }
    if body.latitude is not None and body.longitude is not None:
        geom_sql = "ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326)"
        params["latitude"] = body.latitude
        params["longitude"] = body.longitude

    result = await db.execute(
        text(
            f"""
            INSERT INTO sites (name, geom, habitat_type, location, elevation_m,
                               description, notes, owner_id)
            VALUES (:name, {geom_sql}, :habitat_type, :location, :elevation_m,
                    :description, :notes, :owner_id)
            RETURNING id
            """
        ),
        params,
    )
    new_id = result.scalar()
    await db.commit()

    created = await db.execute(text(_SITE_SELECT + " WHERE s.id = :id"), {"id": new_id})
    return _row_to_site(created.first(), current_user)


@router.delete("/{site_id}", status_code=200)
async def delete_site(
    site_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Hapus lokasi. Ditolak kalau masih ada rekaman yang menunjuk ke lokasi ini.

    Menghapus lokasi berisi rekaman akan membuat rekaman kehilangan konteks
    spasial, jadi pengguna diarahkan memindahkan rekamannya dulu.
    """
    ada = (await db.execute(text("SELECT id FROM sites WHERE id = :id"), {"id": site_id})).first()
    if not ada:
        raise HTTPException(404, "Site not found")

    jumlah = (
        await db.execute(
            text("SELECT count(*) FROM recordings WHERE site_id = :id"), {"id": site_id}
        )
    ).scalar() or 0
    if jumlah:
        raise HTTPException(
            409,
            f"Lokasi ini masih dipakai {jumlah} rekaman. Pindahkan rekamannya dulu, lalu hapus.",
        )

    await db.execute(
        text("DELETE FROM devices WHERE site_id = :id"), {"id": site_id}
    )
    await db.execute(text("DELETE FROM sites WHERE id = :id"), {"id": site_id})
    await db.commit()
    return {"message": "Lokasi dihapus", "site_id": site_id}

