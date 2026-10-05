"""Detections + Species + Jobs routers."""
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_user, get_db, require_admin, require_peneliti, require_verifier
from app.models.tables import (
    Detection,
    Job,
    JobStatus,
    Recording,
    Species,
    User,
    VerifiedStatus,
)
from app.schemas.detection import (
    DetectionResponse,
    PrioritasRequest,
    SpeciesResponse,
    VerifyRequest,
)
from app.services import audit
from app.services.access import (
    can_review_all,
    recording_scope,
    require_recording_access,
    visible_recording_ids,
)
from app.services.queue import enqueue_job

detections_router = APIRouter(tags=["detections"])
species_router = APIRouter(prefix="/api/v1/species", tags=["species"])
jobs_router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])
stats_router = APIRouter(prefix="/api/v1/stats", tags=["stats"])


@detections_router.get("/api/v1/recordings/{recording_id}/detections", response_model=list[DetectionResponse])
async def get_detections(
    recording_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    recording = (await db.execute(select(Recording).where(Recording.id == recording_id))).scalar()
    if recording is None:
        return []
    require_recording_access(recording, current_user)
    result = await db.execute(
        select(Detection, Species)
        .join(Species, Detection.species_id == Species.id)
        .where(Detection.recording_id == recording_id)
        .order_by(Detection.start_s)
    )
    rows = result.all()
    return [
        DetectionResponse(
            id=d.id, recording_id=d.recording_id, species_id=d.species_id,
            species_name=s.scientific_name, species_common=s.common_name_en,
            confidence=d.confidence, start_s=d.start_s, end_s=d.end_s,
            engine=d.engine, engine_version=d.engine_version,
            verified_status=d.verified_status.value, verified_by=d.verified_by,
            azimuth_deg=d.azimuth_deg, azimuth_confidence=d.azimuth_confidence,
            azimuth_kembar_deg=d.azimuth_kembar_deg,
            range_m=d.range_m, localization_engine=d.localization_engine,
        )
        for d, s in rows
    ]


@detections_router.post("/api/v1/detections/{detection_id}/verify")
async def verify_detection(
    detection_id: int,
    body: VerifyRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_verifier),
):
    result = await db.execute(select(Detection).where(Detection.id == detection_id))
    det = result.scalar()
    if not det:
        raise HTTPException(404, "Detection not found")

    if body.status not in ("correct", "incorrect", "uncertain"):
        raise HTTPException(400, "Status tidak valid")

    status_lama = det.verified_status.value if det.verified_status else None
    det.verified_status = VerifiedStatus(body.status)
    det.verified_by = current_user.id
    det.verified_at = datetime.now(UTC)
    # Perubahan dan jejaknya commit bersama, jadi tidak ada verifikasi yang
    # tercatat berubah tanpa jejak siapa yang mengubahnya.
    await audit.catat(
        db,
        "detection.verify",
        actor=current_user,
        entity_type="detection",
        entity_id=det.id,
        detail={
            "status_lama": status_lama,
            "status_baru": body.status,
            "recording_id": det.recording_id,
        },
        request=request,
    )
    await db.commit()
    return {"message": "Verification saved"}


# Species endpoints
@species_router.get("", response_model=list[SpeciesResponse])
async def list_species(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Jumlah deteksi dihitung hanya dari rekaman yang terlihat peran ini. Ini
    # sekaligus mencegah data tamu masuk hitungan staf dan mencegah ranger
    # melihat jumlah deteksi se-kawasan.
    det_count = (
        select(func.count(Detection.id))
        .where(
            Detection.species_id == Species.id,
            Detection.recording_id.in_(visible_recording_ids(current_user)),
        )
        .scalar_subquery()
    )
    result = await db.execute(
        select(Species, det_count.label("detection_count")).order_by(Species.scientific_name)
    )
    rows = result.all()
    return [
        SpeciesResponse(
            id=sp.id, scientific_name=sp.scientific_name,
            common_name_id=sp.common_name_id, common_name_en=sp.common_name_en,
            iucn_status=sp.iucn_status, ebird_code=sp.ebird_code,
            default_threshold=sp.default_threshold, detection_count=cnt,
            model_supported=bool(sp.model_supported),
            prioritas=bool(sp.prioritas), sumber_prioritas=sp.sumber_prioritas,
        )
        for sp, cnt in rows
    ]


@species_router.get("/{species_id}", response_model=SpeciesResponse)
async def get_species(
    species_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    det_count = (
        select(func.count(Detection.id))
        .where(
            Detection.species_id == Species.id,
            Detection.recording_id.in_(visible_recording_ids(current_user)),
        )
        .scalar_subquery()
    )
    result = await db.execute(
        select(Species, det_count.label("detection_count")).where(Species.id == species_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(404, "Species not found")
    sp, cnt = row
    return SpeciesResponse(
        id=sp.id, scientific_name=sp.scientific_name,
        common_name_id=sp.common_name_id, common_name_en=sp.common_name_en,
        iucn_status=sp.iucn_status, ebird_code=sp.ebird_code,
        default_threshold=sp.default_threshold, detection_count=cnt,
        model_supported=bool(sp.model_supported),
        prioritas=bool(sp.prioritas), sumber_prioritas=sp.sumber_prioritas,
    )


@species_router.patch("/{species_id}/prioritas", response_model=SpeciesResponse)
async def set_prioritas(
    species_id: int,
    body: PrioritasRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Admin menandai atau melepas spesies prioritas (sumber 'admin').

    Tanda otomatis dari IUCN atau Permen LHK tidak dihapus di sini; kalau admin
    melepas prioritas pada spesies yang tandanya dari sumber otomatis, sumbernya
    ikut dikosongkan karena keputusan admin berlaku terakhir.
    """
    result = await db.execute(select(Species).where(Species.id == species_id))
    sp = result.scalar()
    if not sp:
        raise HTTPException(404, "Species not found")

    sp.prioritas = body.prioritas
    sp.sumber_prioritas = "admin" if body.prioritas else None
    await db.commit()
    await db.refresh(sp)

    det_count = (
        select(func.count(Detection.id))
        .where(
            Detection.species_id == Species.id,
            Detection.recording_id.in_(visible_recording_ids(current_user)),
        )
        .scalar_subquery()
    )
    row = (
        await db.execute(
            select(Species, det_count.label("detection_count")).where(Species.id == species_id)
        )
    ).first()
    sp, cnt = row
    return SpeciesResponse(
        id=sp.id, scientific_name=sp.scientific_name,
        common_name_id=sp.common_name_id, common_name_en=sp.common_name_en,
        iucn_status=sp.iucn_status, ebird_code=sp.ebird_code,
        default_threshold=sp.default_threshold, detection_count=cnt,
        model_supported=bool(sp.model_supported),
        prioritas=bool(sp.prioritas), sumber_prioritas=sp.sumber_prioritas,
    )


@species_router.get("/{species_id}/detections")
async def species_detections(
    species_id: int,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Deteksi terbaru untuk satu spesies, dipakai halaman detail spesies."""
    from app.models.tables import Site

    result = await db.execute(
        select(Detection, Recording, Site)
        .join(Recording, Recording.id == Detection.recording_id)
        .outerjoin(Site, Site.id == Recording.site_id)
        .where(
            Detection.species_id == species_id,
            Detection.recording_id.in_(visible_recording_ids(current_user)),
        )
        .order_by(Recording.recorded_at.desc().nullslast(), Detection.confidence.desc())
        .limit(limit)
    )
    return [
        {
            "detection_id": det.id,
            "recording_id": rec.id,
            "site_name": site.name if site else None,
            "recorded_at": rec.recorded_at.isoformat() if rec.recorded_at else rec.created_at.isoformat(),
            "confidence": det.confidence,
            "start_s": det.start_s,
            "end_s": det.end_s,
            "engine": det.engine,
            "engine_version": det.engine_version,
            "verified_status": det.verified_status.value,
            "azimuth_deg": det.azimuth_deg,
            "azimuth_confidence": det.azimuth_confidence,
            "azimuth_kembar_deg": det.azimuth_kembar_deg,
            "range_m": det.range_m,
            "localization_engine": det.localization_engine,
        }
        for det, rec, site in result.all()
    ]


# Jobs endpoint
@jobs_router.get("")
async def list_jobs(
    recording_id: int | None = Query(None),
    status: str | None = Query(
        None, pattern="^(active|pending|running|done|failed)$"
    ),
    limit: int = Query(200, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Status job pemrosesan, dipakai UI untuk tombol retry dan indikator progres.

    `status=active` berarti job yang belum selesai, yaitu pending dan running.
    `progress` dan `stage` dikembalikan apa adanya dari worker.
    """
    filters = []
    if recording_id is not None:
        filters.append(Job.recording_id == recording_id)
    if status == "active":
        filters.append(Job.status.in_((JobStatus.pending, JobStatus.running)))
    elif status is not None:
        filters.append(Job.status == JobStatus(status))

    query = (
        select(Job)
        .join(Recording, Recording.id == Job.recording_id)
        .where(recording_scope(current_user))
        .order_by(Job.id.desc())
        .limit(limit)
    )
    if filters:
        query = query.where(*filters)

    jobs = (await db.execute(query)).scalars().all()
    return [
        {
            "id": j.id,
            "recording_id": j.recording_id,
            "status": j.status.value,
            "progress": j.progress,
            "stage": j.stage,
            "attempts": j.attempts,
            "last_error": j.last_error,
            "started_at": j.started_at.isoformat() if j.started_at else None,
            "finished_at": j.finished_at.isoformat() if j.finished_at else None,
        }
        for j in jobs
    ]


@jobs_router.post("/{job_id}/retry")
async def retry_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_verifier),
):
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar()
    if not job:
        raise HTTPException(404, "Job not found")

    job.status = JobStatus.pending
    job.last_error = None
    # Percobaan manual menghitung ulang batas otomatis di worker. Tanpa ini,
    # job yang sudah menyentuh batas akan ditolak walau sengaja diulang manusia.
    job.attempts = 0
    await db.commit()

    try:
        await enqueue_job(job.recording_id)
    except Exception as exc:  # antrean mati, jangan bilang sukses
        job.last_error = f"enqueue gagal: {exc}"[:500]
        await db.commit()
        raise HTTPException(
            503,
            "Job ditandai pending, tapi gagal masuk antrean Redis. "
            "Cek service redis/worker lalu ulangi.",
        ) from exc

    return {"message": "Job re-queued"}


# Stats endpoints
@stats_router.get("/overview")
async def stats_overview(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_peneliti),
):
    recordings = (await db.execute(
        select(func.count(Recording.id)).where(recording_scope(current_user))
    )).scalar() or 0
    detections = (await db.execute(
        select(func.count(Detection.id))
        .join(Recording, Recording.id == Detection.recording_id)
        .where(recording_scope(current_user))
    )).scalar() or 0
    species_count = (await db.execute(
        select(func.count(func.distinct(Detection.species_id)))
        .join(Recording, Recording.id == Detection.recording_id)
        .where(recording_scope(current_user))
    )).scalar() or 0

    from app.models.tables import Site
    sites_count_query = select(func.count(func.distinct(Site.id))).select_from(Site).where(
        Site.khusus_tamu.is_(False)
    )
    if not can_review_all(current_user):
        sites_count_query = sites_count_query.join(Recording, Recording.site_id == Site.id).where(
            Recording.uploaded_by == current_user.id
        )
    sites_count = (await db.execute(sites_count_query)).scalar() or 0

    return {
        "recordings": recordings,
        "detections": detections,
        "species_detected": species_count,
        "sites": sites_count,
    }


@stats_router.get("/species")
async def stats_species(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_peneliti),
):
    result = await db.execute(
        select(
            Species.scientific_name,
            Species.common_name_en,
            func.count(Detection.id).label("count"),
        )
        .join(Detection, Detection.species_id == Species.id)
        .join(Recording, Recording.id == Detection.recording_id)
        .where(recording_scope(current_user))
        .group_by(Species.id)
        .order_by(func.count(Detection.id).desc())
        .limit(limit)
    )
    return [{"scientific_name": r[0], "common_name": r[1], "count": r[2]} for r in result.all()]


@stats_router.get("/timeline")
async def stats_timeline(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_peneliti),
):
    result = await db.execute(
        select(
            func.date_trunc("day", Recording.created_at).label("date"),
            func.count(Detection.id).label("detections"),
        )
        .outerjoin(Detection)
        .where(recording_scope(current_user))
        .group_by("date")
        .order_by("date")
    )
    return [{"date": str(r[0]), "detections": r[1]} for r in result.all()]


