"""Ekspor data untuk peneliti dan petugas lapangan.

Dua keluaran:
1. /api/v1/exports/verified   daftar deteksi terverifikasi, dipakai juga sebagai
   bahan latih ulang classifier (lihat ml/data/from_verifications.py).
2. /api/v1/exports/recordings daftar rekaman beserta jumlah deteksinya.

Format: csv (default) atau json.
"""
import csv
import io

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db, require_peneliti
from app.models.tables import Detection, Recording, Site, User
from app.services.access import recording_scope

router = APIRouter(prefix="/api/v1/exports", tags=["exports"])

VERIFIED_COLUMNS = [
    "detection_id", "recording_id", "site_name", "recorded_at",
    "species_scientific", "species_common", "confidence", "start_s", "end_s",
    "engine", "engine_version", "verified_status", "verified_at",
]

RECORDING_COLUMNS = [
    "recording_id", "site_name", "status", "recorded_at", "duration_s",
    "sample_rate", "detections", "verified_detections",
]


def _csv_response(rows: list[dict], columns: list[str], filename: str):
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=columns)
    writer.writeheader()
    for row in rows:
        writer.writerow({col: row.get(col) for col in columns})
    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/verified")
async def export_verified(
    status: str = Query("correct", pattern="^(correct|incorrect|uncertain|all)$"),
    site: int | None = Query(None),
    format: str = Query("csv", pattern="^(csv|json)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_peneliti),
):
    """Deteksi yang sudah diverifikasi ahli. Default hanya yang ditandai benar."""
    from app.models.tables import Species

    query = (
        select(
            Detection.id, Detection.recording_id, Site.name, Recording.recorded_at,
            Species.scientific_name, Species.common_name_en, Species.common_name_id,
            Detection.confidence, Detection.start_s, Detection.end_s,
            Detection.engine, Detection.engine_version, Detection.verified_status,
            Detection.verified_at,
        )
        .join(Recording, Recording.id == Detection.recording_id)
        .join(Species, Species.id == Detection.species_id)
        .outerjoin(Site, Site.id == Recording.site_id)
        .where(recording_scope(current_user))
        .order_by(Detection.id)
    )
    if status != "all":
        query = query.where(Detection.verified_status == status)
    else:
        query = query.where(Detection.verified_status != "unverified")
    if site is not None:
        query = query.where(Recording.site_id == site)

    rows = [
        {
            "detection_id": r[0], "recording_id": r[1], "site_name": r[2],
            "recorded_at": r[3].isoformat() if r[3] else None,
            "species_scientific": r[4], "species_common": r[5] or r[6],
            "confidence": round(r[7], 4), "start_s": r[8], "end_s": r[9],
            "engine": r[10], "engine_version": r[11],
            "verified_status": r[12].value if hasattr(r[12], "value") else r[12],
            "verified_at": r[13].isoformat() if r[13] else None,
        }
        for r in (await db.execute(query)).all()
    ]

    if format == "json":
        return rows
    return _csv_response(rows, VERIFIED_COLUMNS, "gemahutan_deteksi_terverifikasi.csv")


@router.get("/recordings")
async def export_recordings(
    site: int | None = Query(None),
    format: str = Query("csv", pattern="^(csv|json)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_peneliti),
):
    """Daftar rekaman dengan jumlah deteksi dan jumlah yang sudah diverifikasi."""
    detections = func.count(Detection.id)
    verified = func.count(Detection.id).filter(Detection.verified_status != "unverified")

    query = (
        select(
            Recording.id, Site.name, Recording.status, Recording.recorded_at,
            Recording.duration_s, Recording.sample_rate, detections, verified,
        )
        .outerjoin(Detection, Detection.recording_id == Recording.id)
        .outerjoin(Site, Site.id == Recording.site_id)
        .where(recording_scope(current_user))
        .group_by(Recording.id, Site.name)
        .order_by(Recording.created_at.desc())
    )
    if site is not None:
        query = query.where(Recording.site_id == site)

    rows = [
        {
            "recording_id": r[0], "site_name": r[1],
            "status": r[2].value if hasattr(r[2], "value") else r[2],
            "recorded_at": r[3].isoformat() if r[3] else None,
            "duration_s": round(r[4], 1) if r[4] else None,
            "sample_rate": r[5], "detections": r[6], "verified_detections": r[7],
        }
        for r in (await db.execute(query)).all()
    ]

    if format == "json":
        return rows
    return _csv_response(rows, RECORDING_COLUMNS, "gemahutan_daftar_rekaman.csv")
