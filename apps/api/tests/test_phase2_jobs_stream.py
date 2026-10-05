"""Test siaran status job (SSE): penolakan token dan bentuk event yang dikirim."""
import json
import uuid

import pytest
from app.database import async_session_factory
from app.models.tables import Job, JobStatus, Recording, RecordingStatus
from app.routers import jobs_stream
from helpers_uji import admin


@pytest.mark.anyio
async def test_stream_tanpa_token_401(client):
    resp = await client.get("/api/v1/jobs/stream")
    assert resp.status_code == 401, resp.text


@pytest.mark.anyio
async def test_stream_token_palsu_401(client):
    resp = await client.get("/api/v1/jobs/stream", params={"token": "bukan-token-sah"})
    assert resp.status_code == 401, resp.text


@pytest.mark.anyio
async def test_stream_mengirim_snapshot_job_aktif(client, monkeypatch):
    """Saat sambungan dibuka, semua job aktif dikirim sebagai event job.

    Batas umur sambungan diperpendek supaya test tidak menunggu sepuluh menit;
    yang diuji adalah bentuk event dan isinya, bukan lamanya siaran.
    """
    headers = await admin(client)
    token = headers["Authorization"].split(" ", 1)[1]

    # Job aktif dibuat langsung di basis data supaya hasilnya tidak bergantung
    # pada kecepatan worker memproses berkas.
    penanda = uuid.uuid4().hex[:8]
    async with async_session_factory() as db:
        rekaman = Recording(
            site_id=1,
            uploaded_by=1,
            storage_key=f"uji-stream/{penanda}.wav",
            original_filename=f"stream-{penanda}.wav",
            status=RecordingStatus.pending,
        )
        db.add(rekaman)
        await db.flush()
        job = Job(recording_id=rekaman.id, status=JobStatus.running, progress=35, stage="birdnet")
        db.add(job)
        await db.commit()
        job_id, recording_id = job.id, rekaman.id

    monkeypatch.setattr(jobs_stream, "BATAS_STREAM_DETIK", 1.0)
    monkeypatch.setattr(jobs_stream, "INTERVAL_POLL_DETIK", 0.1)

    try:
        resp = await client.get("/api/v1/jobs/stream", params={"token": token})
        assert resp.status_code == 200, resp.text
        assert resp.headers["content-type"].startswith("text/event-stream")
        assert resp.headers["cache-control"] == "no-cache"

        isi = resp.text
        assert "event: job" in isi
        data = [
            json.loads(baris[len("data: "):])
            for baris in isi.splitlines()
            if baris.startswith("data: ")
        ]
        milik_kita = next(item for item in data if item["job_id"] == job_id)
        assert milik_kita == {
            "recording_id": recording_id,
            "job_id": job_id,
            "status": "running",
            "progress": 35,
            "stage": "birdnet",
        }
    finally:
        async with async_session_factory() as db:
            await db.execute(Job.__table__.delete().where(Job.id == job_id))
            await db.execute(Recording.__table__.delete().where(Recording.id == recording_id))
            await db.commit()


@pytest.mark.anyio
async def test_stream_heartbeat_dan_batas_umur():
    """Sambungan memakai detak 15 detik dan tutup sendiri setelah 10 menit."""
    assert jobs_stream.INTERVAL_HEARTBEAT_DETIK == 15
    assert jobs_stream.BATAS_STREAM_DETIK == 600


@pytest.mark.anyio
async def test_stream_menutup_sambungan_sendiri(client, monkeypatch):
    """Setelah batas umur tercapai, stream ditutup dan tidak menggantung."""
    headers = await admin(client)
    token = headers["Authorization"].split(" ", 1)[1]

    monkeypatch.setattr(jobs_stream, "BATAS_STREAM_DETIK", 0.3)
    monkeypatch.setattr(jobs_stream, "INTERVAL_POLL_DETIK", 0.1)

    resp = await client.get("/api/v1/jobs/stream", params={"token": token})
    assert resp.status_code == 200
    assert resp.text.rstrip().endswith("Sambungkan ulang atau pakai polling.")
