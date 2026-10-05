"""Antrean unggah batch: ringkasan semua batch dan rincian satu batch.

Progres batch dihitung dari progres job tiap rekaman, bukan dari jumlah berkas
yang selesai diunggah, supaya pengguna tahu pekerjaan pemrosesan sudah jalan
sejauh mana.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_user, get_db
from app.models.tables import Job, Recording, RecordingStatus, User
from app.schemas.batch import (
    BatchDetailResponse,
    BatchRecordingItem,
    BatchSummary,
)
from app.services.access import recording_scope

router = APIRouter(prefix="/api/v1/batches", tags=["batches"])


def _persen(nilai) -> int:
    return int(round(float(nilai or 0)))


@router.get("", response_model=list[BatchSummary])
async def list_batches(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(
            Recording.batch_id,
            func.min(Recording.created_at).label("created_at"),
            func.count(Recording.id).label("total"),
            func.count(Recording.id)
            .filter(Recording.status == RecordingStatus.done)
            .label("done"),
            func.count(Recording.id)
            .filter(Recording.status == RecordingStatus.failed)
            .label("failed"),
            func.coalesce(func.avg(Job.progress), 0).label("rata_progres"),
        )
        .outerjoin(Job, Job.recording_id == Recording.id)
        .where(Recording.batch_id.is_not(None), recording_scope(current_user))
        .group_by(Recording.batch_id)
        .order_by(func.min(Recording.created_at).desc())
    )
    return [
        BatchSummary(
            batch_id=row.batch_id,
            created_at=row.created_at.isoformat() if row.created_at else None,
            total=row.total,
            done=row.done,
            failed=row.failed,
            progress_percent=_persen(row.rata_progres),
        )
        for row in result.all()
    ]


@router.get("/{batch_id}", response_model=BatchDetailResponse)
async def get_batch(
    batch_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Recording, Job)
        .outerjoin(Job, Job.recording_id == Recording.id)
        .where(Recording.batch_id == batch_id, recording_scope(current_user))
        .order_by(Recording.id)
    )
    rows = result.all()
    if not rows:
        raise HTTPException(404, "Batch tidak ditemukan")

    hitung = {s.value: 0 for s in RecordingStatus}
    progres_items: list[BatchRecordingItem] = []
    for recording, job in rows:
        hitung[recording.status.value] += 1
        progres_items.append(
            BatchRecordingItem(
                id=recording.id,
                filename=recording.original_filename
                or (recording.storage_key.rsplit("/", 1)[-1] or ""),
                status=recording.status.value,
                progress=job.progress if job else 0,
                stage=job.stage if job else None,
            )
        )

    rata = sum(item.progress for item in progres_items) / len(progres_items)
    return BatchDetailResponse(
        batch_id=batch_id,
        total=len(rows),
        done=hitung["done"],
        failed=hitung["failed"],
        pending=hitung["pending"],
        processing=hitung["processing"],
        progress_percent=_persen(rata),
        recordings=progres_items,
    )
