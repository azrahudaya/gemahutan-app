"""Recordings router: upload, list, detail."""
import json
import shutil
import subprocess
import tempfile
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.deps import get_current_user, get_current_user_flexible, get_db
from app.models.tables import Device, Job, JobStatus, Recording, RecordingStatus, Site, User
from app.schemas.batch import BatchItemResult, BatchUploadResponse
from app.schemas.recording import (
    RecordingListResponse,
    RecordingResponse,
    RecordingUpdate,
)
from app.services.access import recording_scope, require_recording_access
from app.services.queue import enqueue_job
from app.services.spectrogram_cache import cache_spectrogram_key as _kunci_cache_spektrogram
from app.services.storage import ensure_bucket, s3_client, upload_fileobj

router = APIRouter(prefix="/api/v1/recordings", tags=["recordings"])

# Tipe MIME yang diterima. Daftarnya harus memuat semua ekstensi di
# ALLOWED_EXTENSIONS, termasuk m4a/aac dari rekaman ponsel, ogg, dan webm dari
# perekam di browser. Sebelumnya m4a dan ogg diizinkan berdasarkan ekstensi
# tetapi ditolak di sini, jadi unggahan dari ponsel selalu gagal dengan pesan
# "tipe file tidak didukung".
ALLOWED_TYPES = {
    "audio/wav", "audio/x-wav", "audio/wave",
    "audio/mpeg", "audio/mp3",
    "audio/flac", "audio/x-flac",
    "audio/ogg", "audio/opus",
    "audio/mp4", "audio/m4a", "audio/x-m4a", "audio/aac",
    "audio/webm", "video/webm",
    "application/octet-stream",
}
ALLOWED_EXTENSIONS = {"wav", "mp3", "flac", "ogg", "m4a", "aac", "opus", "webm"}
MAX_SIZE = 200 * 1024 * 1024  # 200 MB
UPLOAD_CHUNK = 1024 * 1024

# Batas berkas per unggahan batch. Lebih dari ini satu permintaan bisa menahan
# koneksi dan memori terlalu lama.
MAX_BATCH_FILES = 20


def _ekstensi(filename: str) -> str:
    if "." not in filename:
        raise HTTPException(
            400, "Nama file harus punya ekstensi audio, misal rekaman.wav"
        )
    ext = filename.rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            400,
            f"Ekstensi .{ext} tidak didukung. Pakai salah satu dari: "
            + ", ".join(sorted(ALLOWED_EXTENSIONS)),
        )
    return ext


def _periksa_tipe(file: UploadFile) -> tuple[str, str]:
    """Kembalikan (content_type, ekstensi) setelah lolos pemeriksaan."""
    # MediaRecorder mengirim parameter codec ("audio/webm;codecs=opus"); bandingkan tipe dasarnya saja.
    ct = (file.content_type or "application/octet-stream").split(";", 1)[0].strip().lower()
    if ct not in ALLOWED_TYPES:
        raise HTTPException(400, f"Tipe file tidak didukung: {ct}")
    return ct, _ekstensi(file.filename or "")


def _periksa_ukuran(file: UploadFile) -> None:
    """Batas ukuran ditegakkan sebelum unggah: hitung potongan yang dibaca."""
    consumed = 0
    while True:
        chunk = file.file.read(UPLOAD_CHUNK)
        if not chunk:
            break
        consumed += len(chunk)
        if consumed > MAX_SIZE:
            raise HTTPException(
                413,
                f"Ukuran file lebih dari {MAX_SIZE // (1024 * 1024)} MB. "
                "Potong rekaman dulu sebelum diunggah.",
            )
    if consumed == 0:
        raise HTTPException(400, "File kosong")
    file.file.seek(0)


def _durasi_format(metadata: dict) -> float | None:
    """Durasi dari metadata format; None kalau hilang, kosong, atau \"N/A\".

    WebM buatan MediaRecorder Chrome tidak menulis durasi di header, jadi
    ffprobe mengembalikan objek format tanpa kunci duration (atau \"N/A\").
    """
    raw = (metadata.get("format") or {}).get("duration")
    if raw is None:
        return None
    try:
        durasi = float(raw)
    except (ValueError, TypeError):
        return None
    return durasi if durasi > 0 else None


def _hitung_durasi(jalur: str, ffmpeg: str) -> float | None:
    """Durasi dengan mendekode penuh ke null sink, baca waktu terakhir ffmpeg.

    Dipakai hanya untuk berkas tanpa durasi di header (WebM MediaRecorder),
    yang biasanya rekaman pendek. Tanpa -v error supaya progress time= muncul.
    """
    import re

    hasil = subprocess.run(
        [ffmpeg, "-nostdin", "-i", jalur, "-map", "0:a:0", "-f", "null", "-"],
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    cocok = re.findall(r"time=(\d+):(\d+):(\d+(?:\.\d+)?)", hasil.stderr or "")
    if not cocok:
        return None
    jam, menit, detik = cocok[-1]
    durasi = int(jam) * 3600 + int(menit) * 60 + float(detik)
    return durasi if durasi > 0 else None


def _validasi_audio(file: UploadFile) -> None:
    """Pastikan isi file benar-benar audio sebelum menyentuh object storage."""
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise HTTPException(503, "Validator audio belum tersedia di server")

    sementara = tempfile.NamedTemporaryFile(suffix=".audio", delete=False)
    jalur = sementara.name
    try:
        with sementara:
            file.file.seek(0)
            shutil.copyfileobj(file.file, sementara)
        hasil = subprocess.run(
            [
                ffprobe,
                "-v", "error",
                "-show_entries", "format=duration:stream=codec_type,channels,sample_rate",
                "-of", "json",
                jalur,
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
        if hasil.returncode != 0:
            raise HTTPException(415, "Isi file bukan audio yang valid")
        try:
            metadata = json.loads(hasil.stdout)
        except json.JSONDecodeError:
            raise HTTPException(415, "Metadata audio tidak bisa dibaca") from None
        streams = metadata.get("streams") or []
        audio_streams = [stream for stream in streams if stream.get("codec_type") == "audio"]
        if not audio_streams:
            raise HTTPException(415, "File tidak memiliki stream audio yang valid")

        duration = _durasi_format(metadata)
        if duration is None:
            # WebM tanpa durasi (MediaRecorder Chrome) punya stream audio tetapi
            # tidak menulis durasi di header. Hitung dengan mendekode lewat ffmpeg.
            ffmpeg = shutil.which("ffmpeg")
            duration = _hitung_durasi(jalur, ffmpeg) if ffmpeg else None
            if duration is None:
                raise HTTPException(415, "File tidak memiliki stream audio yang valid")
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(408, "Validasi audio melewati batas waktu") from exc
    finally:
        file.file.seek(0)
        try:
            import os
            os.unlink(jalur)
        except FileNotFoundError:
            pass


async def _cek_site_dan_perangkat(
    db: AsyncSession, site_id: int, device_id: int | None
) -> None:
    lokasi = (await db.execute(select(Site.id).where(Site.id == site_id))).scalar()
    if not lokasi:
        raise HTTPException(400, f"Lokasi {site_id} tidak ada")
    if device_id is not None:
        perangkat = (
            await db.execute(
                select(Device.site_id, Device.active).where(Device.id == device_id)
            )
        ).first()
        if not perangkat:
            raise HTTPException(400, f"Perangkat {device_id} tidak ada")
        if perangkat.site_id != site_id:
            raise HTTPException(400, "Perangkat tidak terpasang di lokasi yang dipilih")
        if not perangkat.active:
            raise HTTPException(400, "Perangkat tidak aktif")


async def _simpan_rekaman(
    file: UploadFile,
    *,
    site_id: int,
    device_id: int | None,
    rec_at: datetime | None,
    user_id: int,
    batch_id: str | None,
    db: AsyncSession,
) -> Recording:
    """Simpan satu berkas ke storage lalu buat baris rekaman dan jobnya.

    Dipakai unggahan tunggal dan unggahan batch supaya pemeriksaan tipe, batas
    ukuran, dan pembuatan job tidak berbeda antara dua jalur itu.
    """
    from asyncio import to_thread

    ct, ext = _periksa_tipe(file)
    _periksa_ukuran(file)
    await to_thread(_validasi_audio, file)

    storage_key = f"recordings/{uuid.uuid4().hex}.{ext}"
    ensure_bucket()
    await to_thread(upload_fileobj, file.file, storage_key, content_type=ct)

    recording = Recording(
        site_id=site_id,
        device_id=device_id,
        uploaded_by=user_id,
        storage_key=storage_key,
        original_filename=(file.filename or "")[:255] or None,
        batch_id=batch_id,
        recorded_at=rec_at,
        status=RecordingStatus.pending,
    )
    db.add(recording)
    await db.flush()
    db.add(Job(recording_id=recording.id, status=JobStatus.pending))
    await db.commit()
    await db.refresh(recording)
    return recording


def _parse_range(header: str | None) -> tuple[int, int] | None:
    if not header:
        return None
    if not header.startswith("bytes=") or "," in header:
        raise HTTPException(416, "Rentang byte tidak didukung")
    nilai = header[6:].strip()
    if "-" not in nilai:
        raise HTTPException(416, "Rentang byte tidak valid")
    awal, akhir = nilai.split("-", 1)
    try:
        if not awal:
            jumlah = int(akhir)
            if jumlah <= 0:
                raise ValueError
            return -jumlah, -1
        start = int(awal)
        end = int(akhir) if akhir else start + (8 * 1024 * 1024) - 1
    except ValueError:
        raise HTTPException(416, "Rentang byte tidak valid") from None
    if start < 0 or end < start:
        raise HTTPException(416, "Rentang byte tidak valid")
    return start, end


def _waktu_rekaman(recorded_at: str | None) -> datetime | None:
    if not recorded_at:
        return None
    try:
        return datetime.fromisoformat(recorded_at)
    except ValueError:
        return None


@router.post("", response_model=RecordingResponse, status_code=201)
async def upload_recording(
    file: UploadFile = File(...),
    site_id: int = Form(...),
    device_id: int | None = Form(None),
    recorded_at: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _cek_site_dan_perangkat(db, site_id, device_id)
    recording = await _simpan_rekaman(
        file,
        site_id=site_id,
        device_id=device_id,
        rec_at=_waktu_rekaman(recorded_at),
        user_id=current_user.id,
        batch_id=None,
        db=db,
    )
    # Respons disusun sebelum commit atau rollback berikutnya: commit membuat
    # atribut objek kedaluwarsa, dan pembacaan atribut kedaluwarsa di sesi async
    # berakhir dengan MissingGreenlet.
    response = _to_response(recording)

    # Enqueue processing. Kalau antrean gagal, catat alasannya di job supaya
    # endpoint /jobs/{id}/retry dan sweep worker tahu ini perlu diulang.
    queued = True
    queue_error = None
    try:
        await enqueue_job(recording.id)
    except Exception as exc:
        queued = False
        queue_error = str(exc)[:500]

    if not queued:
        from sqlalchemy import update as sa_update
        await db.execute(
            sa_update(Job).where(Job.recording_id == recording.id).values(last_error=queue_error)
        )
        await db.commit()

    return JSONResponse(
        status_code=201 if queued else 202,
        content={**response.model_dump(), "queued": queued, "queue_error": queue_error},
    )


@router.post("/batch", response_model=BatchUploadResponse, status_code=201)
async def upload_batch(
    files: list[UploadFile] = File(...),
    site_id: int = Form(...),
    device_id: int | None = Form(None),
    recorded_at: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Unggah 1 sampai 20 berkas sekaligus dalam satu batch.

    Satu berkas yang ditolak tidak membatalkan berkas lain: pemeriksaan tipe dan
    batas ukuran berlaku per berkas, dan alasan penolakan ditulis di item itu.
    """
    if not files:
        raise HTTPException(400, "Tidak ada berkas yang diunggah")
    if len(files) > MAX_BATCH_FILES:
        raise HTTPException(
            400,
            f"Maksimal {MAX_BATCH_FILES} berkas per unggahan batch, "
            f"permintaan ini berisi {len(files)} berkas.",
        )

    await _cek_site_dan_perangkat(db, site_id, device_id)
    batch_id = uuid.uuid4().hex
    rec_at = _waktu_rekaman(recorded_at)
    # Dibaca sekali di luar perulangan: rollback di tengah batch membuat atribut
    # objek kedaluwarsa, dan membacanya lagi di sesi async akan gagal.
    user_id = current_user.id

    items: list[BatchItemResult] = []
    for file in files:
        nama = file.filename or ""
        try:
            recording = await _simpan_rekaman(
                file,
                site_id=site_id,
                device_id=device_id,
                rec_at=rec_at,
                user_id=user_id,
                batch_id=batch_id,
                db=db,
            )
        except HTTPException as exc:
            await db.rollback()
            items.append(
                BatchItemResult(
                    filename=nama,
                    recording_id=None,
                    status="failed",
                    error=str(exc.detail),
                )
            )
            continue
        except Exception as exc:
            await db.rollback()
            items.append(
                BatchItemResult(
                    filename=nama,
                    recording_id=None,
                    status="failed",
                    error=f"gagal menyimpan berkas: {str(exc)[:300]}",
                )
            )
            continue

        recording_id = recording.id
        status_awal = recording.status.value

        try:
            await enqueue_job(recording_id)
        except Exception as exc:
            # Baris rekaman tetap ada dan job tetap pending, jadi bisa diulang
            # dari halaman antrean. Alasannya dicatat di job.
            from sqlalchemy import update as sa_update
            await db.execute(
                sa_update(Job)
                .where(Job.recording_id == recording_id)
                .values(last_error=f"enqueue gagal: {exc}"[:500])
            )
            await db.commit()

        items.append(
            BatchItemResult(
                filename=nama,
                recording_id=recording_id,
                status=status_awal,
                error=None,
            )
        )

    diterima = sum(1 for item in items if item.recording_id is not None)
    return BatchUploadResponse(
        batch_id=batch_id,
        count=len(items),
        accepted=diterima,
        failed=len(items) - diterima,
        items=items,
    )


@router.get("", response_model=RecordingListResponse)
async def list_recordings(
    site: int | None = Query(None),
    device: int | None = Query(None),
    species: int | None = Query(None),
    species_q: str | None = Query(None, max_length=120),
    min_conf: float | None = Query(None, ge=0, le=1),
    status: str | None = Query(None, pattern="^(pending|processing|done|failed)$"),
    from_date: str | None = Query(None, alias="from"),
    to_date: str | None = Query(None, alias="to"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Daftar rekaman dengan filter lokasi, perangkat, spesies, confidence, status, dan tanggal.

    Nama parameter mengikuti yang dipakai frontend: site, device, species,
    species_q, min_conf, status, from, to, page, page_size. Respons menyertakan
    total_pages supaya kontrol paginasi bisa dihitung.
    """
    from app.models.tables import Detection, Species

    filters = []
    if site is not None:
        filters.append(Recording.site_id == site)
    if device is not None:
        filters.append(Recording.device_id == device)
    if status is not None:
        filters.append(Recording.status == RecordingStatus(status))

    if from_date:
        try:
            filters.append(Recording.recorded_at >= datetime.fromisoformat(from_date))
        except ValueError:
            raise HTTPException(400, "Format tanggal 'from' harus YYYY-MM-DD") from None
    if to_date:
        try:
            parsed = datetime.fromisoformat(to_date)
            # Tanggal akhir inklusif sampai akhir hari.
            if parsed.hour == 0 and parsed.minute == 0:
                parsed = parsed.replace(hour=23, minute=59, second=59)
            filters.append(Recording.recorded_at <= parsed)
        except ValueError:
            raise HTTPException(400, "Format tanggal 'to' harus YYYY-MM-DD") from None

    needs_detection_join = species is not None or species_q or min_conf is not None

    query = select(Recording)
    count_query = select(func.count(func.distinct(Recording.id)))

    if needs_detection_join:
        query = query.join(Detection, Detection.recording_id == Recording.id)
        count_query = count_query.join(Detection, Detection.recording_id == Recording.id)
        if species is not None:
            filters.append(Detection.species_id == species)
        if min_conf is not None:
            filters.append(Detection.confidence >= min_conf)
        if species_q:
            query = query.join(Species, Species.id == Detection.species_id)
            count_query = count_query.join(Species, Species.id == Detection.species_id)
            like = f"%{species_q.strip()}%"
            filters.append(
                or_(
                    Species.scientific_name.ilike(like),
                    Species.common_name_id.ilike(like),
                    Species.common_name_en.ilike(like),
                )
            )
        # Satu rekaman bisa punya beberapa deteksi yang cocok, jadi hasilnya di-distinct.
        query = query.distinct()

    for condition in filters:
        query = query.where(condition)
        count_query = count_query.where(condition)

    visibility = recording_scope(current_user)
    query = query.where(visibility)
    count_query = count_query.where(visibility)

    total = (await db.execute(count_query)).scalar() or 0
    total_pages = max(1, (total + page_size - 1) // page_size)

    query = query.order_by(Recording.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    recordings = (await db.execute(query)).scalars().all()

    ids = [r.id for r in recordings]
    counts: dict[int, int] = {}
    site_names: dict[int, str] = {}
    job_state: dict[int, Job] = {}
    if ids:
        from sqlalchemy import func as sa_func

        count_rows = await db.execute(
            select(Detection.recording_id, sa_func.count(Detection.id))
            .where(Detection.recording_id.in_(ids))
            .group_by(Detection.recording_id)
        )
        counts = {rid: cnt for rid, cnt in count_rows.all()}

        site_rows = await db.execute(select(Site.id, Site.name))
        site_names = {sid: sname for sid, sname in site_rows.all()}

        job_rows = await db.execute(select(Job).where(Job.recording_id.in_(ids)))
        job_state = {j.recording_id: j for j in job_rows.scalars().all()}

    return RecordingListResponse(
        items=[
            _to_response(
                r, counts.get(r.id, 0), site_names.get(r.site_id), job_state.get(r.id)
            )
            for r in recordings
        ],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{recording_id}", response_model=RecordingResponse)
async def get_recording(
    recording_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Recording).where(Recording.id == recording_id))
    recording = require_recording_access(result.scalar(), current_user)

    from sqlalchemy import func as sa_func

    from app.models.tables import Detection
    count = (
        await db.execute(
            select(sa_func.count(Detection.id)).where(Detection.recording_id == recording_id)
        )
    ).scalar() or 0
    site_name = (
        await db.execute(select(Site.name).where(Site.id == recording.site_id))
    ).scalar()
    job = (
        await db.execute(select(Job).where(Job.recording_id == recording_id))
    ).scalar()
    return _to_response(recording, count, site_name, job)


@router.get("/{recording_id}/audio")
async def stream_audio(
    recording_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_flexible),
):
    """Stream audio asli dari MinIO supaya waveform player bisa dipakai."""
    from botocore.exceptions import ClientError

    from app.services.storage import object_exists
    settings = get_settings()

    result = await db.execute(select(Recording).where(Recording.id == recording_id))
    recording = require_recording_access(result.scalar(), current_user)

    if not object_exists(recording.storage_key):
        raise HTTPException(
            404,
            "Audio untuk rekaman ini tidak ada di storage. "
            "Baris rekaman tanpa berkas audio biasanya sisa data demo lama, "
            "hapus atau unggah ulang audionya.",
        )

    ext = recording.storage_key.rsplit(".", 1)[-1].lower()
    media_type = {
        "wav": "audio/wav",
        "mp3": "audio/mpeg",
        "flac": "audio/flac",
        "ogg": "audio/ogg",
        "m4a": "audio/mp4",
        "webm": "audio/webm",
    }.get(ext, "application/octet-stream")

    rentang = _parse_range(request.headers.get("range"))
    parameter = {"Bucket": settings.s3_bucket, "Key": recording.storage_key}
    ukuran_awal: int | None = None
    if rentang:
        # Suffix range (-N) perlu ukuran objek sebelum diterjemahkan ke range S3.
        if rentang[0] < 0:
            kepala = s3_client.head_object(Bucket=settings.s3_bucket, Key=recording.storage_key)
            ukuran_awal = int(kepala["ContentLength"])
            panjang = min(-rentang[0], ukuran_awal)
            rentang = (ukuran_awal - panjang, ukuran_awal - 1)
        parameter["Range"] = f"bytes={rentang[0]}-{rentang[1]}"

    try:
        obj = s3_client.get_object(**parameter)
    except ClientError as exc:
        print(f"[audio] gagal membaca storage untuk rekaman {recording_id}: {exc}")
        raise HTTPException(502, "Gagal membaca berkas audio dari storage.") from exc

    def _iter_body(body, chunk=64 * 1024):
        while True:
            data = body.read(chunk)
            if not data:
                break
            yield data

    headers = {"Accept-Ranges": "bytes", "Cache-Control": "private, max-age=300"}
    status_code = 200
    if rentang:
        content_range = obj.get("ContentRange")
        if not content_range:
            total = ukuran_awal or int(obj.get("ContentLength", 0))
            content_range = f"bytes {rentang[0]}-{rentang[1]}/{total}"
        headers["Content-Range"] = content_range
        headers["Content-Length"] = str(obj["ContentLength"])
        status_code = 206
    elif obj.get("ContentLength"):
        headers["Content-Length"] = str(obj["ContentLength"])
    return StreamingResponse(
        _iter_body(obj["Body"]), media_type=media_type, headers=headers, status_code=status_code
    )


@router.patch("/{recording_id}", response_model=RecordingResponse)
async def update_recording(
    recording_id: int,
    body: RecordingUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Koreksi metadata rekaman: lokasi, perangkat, atau waktu perekaman.

    Hanya pengunggah dan admin yang boleh mengubah. Isi audio dan hasil
    analisis tidak diubah di sini.
    """
    from sqlalchemy import func as sa_func

    from app.models.tables import Detection, UserRole

    result = await db.execute(select(Recording).where(Recording.id == recording_id))
    recording = result.scalar()
    if recording is None:
        raise HTTPException(404, "Rekaman tidak ditemukan")

    if recording.uploaded_by != current_user.id and current_user.role != UserRole.admin:
        raise HTTPException(403, "Hanya pengunggah atau admin yang boleh mengubah rekaman ini.")

    if body.site_id is not None:
        site = (await db.execute(select(Site.id).where(Site.id == body.site_id))).scalar()
        if not site:
            raise HTTPException(400, f"Lokasi {body.site_id} tidak ada")
        recording.site_id = body.site_id

    if body.device_id is not None:
        recording.device_id = body.device_id
    if body.recorded_at is not None:
        recording.recorded_at = body.recorded_at

    await _cek_site_dan_perangkat(db, recording.site_id, recording.device_id)
    await db.commit()
    await db.refresh(recording)

    count = (
        await db.execute(
            select(sa_func.count(Detection.id)).where(Detection.recording_id == recording_id)
        )
    ).scalar() or 0
    site_name = (
        await db.execute(select(Site.name).where(Site.id == recording.site_id))
    ).scalar()
    job = (
        await db.execute(select(Job).where(Job.recording_id == recording_id))
    ).scalar()
    return _to_response(recording, count, site_name, job)


@router.delete("/{recording_id}", status_code=200)
async def delete_recording(
    recording_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Hapus rekaman beserta deteksi, indeks, job, dan berkas audionya.

    Salah unggah sebelumnya tidak bisa dibatalkan sama sekali dari aplikasi,
    jadi barisnya menumpuk dan hanya bisa dibersihkan lewat SQL manual.
    """
    from sqlalchemy import delete as sa_delete
    from sqlalchemy import func as sa_func

    from app.models.tables import AcousticIndex, Detection, UserRole
    from app.services.storage import delete_object

    result = await db.execute(select(Recording).where(Recording.id == recording_id))
    recording = result.scalar()
    if recording is None:
        raise HTTPException(404, "Rekaman tidak ditemukan")

    if recording.uploaded_by != current_user.id and current_user.role != UserRole.admin:
        raise HTTPException(403, "Hanya pengunggah atau admin yang boleh menghapus rekaman ini.")

    storage_key = recording.storage_key
    audio_terhapus = delete_object(storage_key)
    if not audio_terhapus:
        raise HTTPException(502, "Audio belum bisa dihapus dari storage; rekaman dipertahankan")

    jumlah_deteksi = (
        await db.execute(
            select(sa_func.count(Detection.id)).where(Detection.recording_id == recording_id)
        )
    ).scalar() or 0

    await db.execute(sa_delete(Detection).where(Detection.recording_id == recording_id))
    await db.execute(sa_delete(AcousticIndex).where(AcousticIndex.recording_id == recording_id))
    await db.execute(sa_delete(Job).where(Job.recording_id == recording_id))
    await db.execute(sa_delete(Recording).where(Recording.id == recording_id))
    await db.commit()

    # Cache spektrogram tidak lagi punya baris database setelah commit.
    delete_object(_kunci_cache_spektrogram(storage_key))

    return {
        "message": "Rekaman dihapus",
        "recording_id": recording_id,
        "detections_terhapus": int(jumlah_deteksi),
        "audio_terhapus": audio_terhapus,
    }


def _nama_berkas(r: Recording) -> str | None:
    """Nama berkas asli, atau nama objek di storage kalau baris lama belum punya."""
    if r.original_filename:
        return r.original_filename
    return r.storage_key.rsplit("/", 1)[-1] or None


def _to_response(
    r: Recording,
    detection_count: int = 0,
    site_name: str | None = None,
    job: Job | None = None,
) -> RecordingResponse:
    return RecordingResponse(
        id=r.id,
        site_id=r.site_id,
        device_id=r.device_id,
        uploaded_by=r.uploaded_by,
        storage_key=r.storage_key,
        filename=_nama_berkas(r),
        batch_id=r.batch_id,
        site_name=site_name,
        detection_count=detection_count,
        duration_s=r.duration_s,
        sample_rate=r.sample_rate,
        recorded_at=r.recorded_at.isoformat() if r.recorded_at else None,
        status=r.status.value,
        progress=job.progress if job else 0,
        stage=job.stage if job else None,
        error_message=r.error_message,
        created_at=r.created_at.isoformat(),
    )
