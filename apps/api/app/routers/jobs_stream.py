"""Siaran status job lewat Server-Sent Events.

Bukan pengganti polling, hanya pelengkap: klien tetap wajib fallback polling 5
detik kalau sambungan ini gagal. Token dikirim lewat query string karena
EventSource tidak bisa menyetel header Authorization, jadi endpoint ini satu-
satunya yang menerima token di URL dan tidak memakai header Bearer.
"""
import asyncio
import json
import time

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from app.database import async_session_factory
from app.deps import user_from_token
from app.models.tables import Job, JobStatus, Recording, User
from app.services.access import recording_scope

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])

# Jeda antar pemeriksaan perubahan, detak jantung supaya proxy tidak memutus
# sambungan, dan batas umur sambungan supaya tidak ada koneksi menggantung.
INTERVAL_POLL_DETIK = 2
INTERVAL_HEARTBEAT_DETIK = 15
BATAS_STREAM_DETIK = 600
MAKS_JOB_AKTIF = 200


def _payload(job: Job) -> str:
    return json.dumps(
        {
            "recording_id": job.recording_id,
            "job_id": job.id,
            "status": job.status.value,
            "progress": job.progress,
            "stage": job.stage,
        }
    )


async def _aliran_job(current_user: User):
    """Kirim snapshot job aktif saat sambungan dibuka, lalu tiap ada perubahan."""
    mulai = time.monotonic()
    detak_terakhir = time.monotonic()
    terkirim: dict[int, tuple[str, int, str | None]] = {}

    yield ": tersambung ke siaran status job\n\n"

    while time.monotonic() - mulai < BATAS_STREAM_DETIK:
        kondisi = Job.status.in_((JobStatus.pending, JobStatus.running))
        if terkirim:
            # Job yang sudah selesai atau gagal tetap dipantau sekali lagi supaya
            # keadaan akhirnya ikut terkirim, bukan berhenti di progres terakhir.
            kondisi = kondisi | Job.id.in_(list(terkirim))

        async with async_session_factory() as db:
            baris = (
                await db.execute(
                    select(Job)
                    .join(Recording, Recording.id == Job.recording_id)
                    .where(kondisi, recording_scope(current_user))
                    .order_by(Job.id)
                    .limit(MAKS_JOB_AKTIF)
                )
            ).scalars().all()

        for job in baris:
            keadaan = (job.status.value, job.progress, job.stage)
            if terkirim.get(job.id) != keadaan:
                terkirim[job.id] = keadaan
                yield f"event: job\ndata: {_payload(job)}\n\n"
                detak_terakhir = time.monotonic()

        if time.monotonic() - detak_terakhir >= INTERVAL_HEARTBEAT_DETIK:
            yield ": heartbeat\n\n"
            detak_terakhir = time.monotonic()

        await asyncio.sleep(INTERVAL_POLL_DETIK)

    yield ": batas 10 menit, stream ditutup. Sambungkan ulang atau pakai polling.\n\n"


@router.get("/stream")
async def stream_jobs(request: Request):
    token = request.query_params.get("token")
    if not token:
        header = request.headers.get("authorization", "")
        if header.lower().startswith("bearer "):
            token = header[len("bearer "):].strip()

    # Tanpa token sah jawab 401, bukan membuka sambungan yang tidak diawasi.
    user = await user_from_token(token)

    return StreamingResponse(
        _aliran_job(user),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
