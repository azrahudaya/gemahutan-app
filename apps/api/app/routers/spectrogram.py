"""Spectrogram endpoint: PNG dari audio yang tersimpan di MinIO."""
import io
import math
import os
import subprocess
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.deps import get_current_user, get_db, require_peneliti
from app.models.tables import Recording, User
from app.services.access import recording_scope, require_recording_access
from app.services.spectrogram_cache import cache_spectrogram_key
from app.services.storage import get_bytes, object_exists, put_bytes, s3_client

router = APIRouter(tags=["spectrogram"])
settings = get_settings()

DECODE_LANGSUNG = {".wav", ".mp3", ".flac", ".ogg", ".opus", ".aiff", ".aif"}


def _transcode_ke_wav(jalur: str) -> str | None:
    """Konversi audio ke wav lewat ffmpeg, atau None kalau gagal.

    Rekaman langsung dari ponsel biasanya m4a atau aac, dan libsndfile tidak
    membacanya. Tanpa langkah ini, unggahan m4a lolos di API lalu spektrogramnya
    tidak bisa dibuat.
    """
    import shutil

    if not shutil.which("ffmpeg"):
        return None

    tujuan = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tujuan.close()
    proses = subprocess.run(
        ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", jalur,
         "-ar", "48000", "-ac", "1", tujuan.name],
        capture_output=True,
        text=True,
    )
    if proses.returncode != 0 or os.path.getsize(tujuan.name) == 0:
        if os.path.exists(tujuan.name):
            os.unlink(tujuan.name)
        return None
    return tujuan.name


@router.get("/api/v1/recordings/{recording_id}/spectrogram")
async def get_spectrogram(
    recording_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Recording).where(Recording.id == recording_id))
    recording = require_recording_access(result.scalar(), current_user)

    # Tanpa berkas audio, tidak ada yang bisa digambar. Balas 404 yang jelas,
    # bukan 500 dari dalam librosa.
    if not object_exists(recording.storage_key):
        raise HTTPException(
            404,
            "Audio untuk rekaman ini tidak ada di storage, jadi spektrogram tidak bisa dibuat.",
        )

    # Hasil render sebelumnya dipakai ulang kalau ada. Isi cache selalu sama
    # dengan hasil render karena kuncinya diturunkan dari berkas audio.
    kunci_cache = cache_spectrogram_key(recording.storage_key)
    tersimpan = get_bytes(kunci_cache)
    if tersimpan:
        return StreamingResponse(
            io.BytesIO(tersimpan),
            media_type="image/png",
            headers={"Cache-Control": "private, max-age=86400", "X-Spektrogram-Cache": "hit"},
        )

    tmp = tempfile.NamedTemporaryFile(
        suffix=Path(recording.storage_key).suffix.lower() or ".wav", delete=False
    )
    tmp.close()
    tmp_wav: str | None = None
    try:
        with open(tmp.name, "wb") as fh:
            s3_client.download_fileobj(settings.s3_bucket, recording.storage_key, fh)

        import librosa
        import librosa.display
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np

        try:
            y, sr = librosa.load(tmp.name, sr=None, mono=True)
        except Exception as exc:
            tmp_wav = _transcode_ke_wav(tmp.name)
            if not tmp_wav:
                # Detail teknis masuk log, bukan ke klien.
                print(f"[spectrogram] gagal dekode rekaman {recording_id}: {exc}")
                raise HTTPException(
                    415,
                    "Format audio tidak dikenali. Unggah ulang sebagai wav, mp3, atau flac.",
                ) from exc
            y, sr = librosa.load(tmp_wav, sr=None, mono=True)

        if y.size == 0:
            raise HTTPException(422, "Berkas audio kosong, tidak ada sinyal untuk digambar")

        S = librosa.feature.melspectrogram(y=y, sr=sr, n_mels=128, fmax=sr // 2)
        S_dB = librosa.power_to_db(S, ref=np.max)

        # Warna figure disamakan dengan kartu gelap di UI supaya gambar tidak
        # tampak seperti tempelan putih di tengah dashboard.
        fig, ax = plt.subplots(1, 1, figsize=(12, 4), dpi=100)
        fig.patch.set_facecolor("#101010")
        ax.set_facecolor("#101010")
        img = librosa.display.specshow(S_dB, sr=sr, x_axis="time", y_axis="mel",
                                       ax=ax, cmap="magma")
        cbar = fig.colorbar(img, ax=ax, format="%+2.0f dB")
        ax.set_title("")
        for text in (ax.xaxis.label, ax.yaxis.label, *ax.get_xticklabels(), *ax.get_yticklabels()):
            text.set_color("#D4D4D8")
        for spine in ax.spines.values():
            spine.set_color("#27272A")
        cbar.ax.tick_params(colors="#D4D4D8")
        cbar.outline.set_edgecolor("#27272A")
        fig.tight_layout()

        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight", pad_inches=0.1)
        plt.close(fig)
        isi = buf.getvalue()
        put_bytes(kunci_cache, isi, "image/png")

        return StreamingResponse(
            io.BytesIO(isi),
            media_type="image/png",
            headers={"Cache-Control": "private, max-age=86400", "X-Spektrogram-Cache": "miss"},
        )
    finally:
        for berkas in (tmp.name, tmp_wav):
            if berkas and os.path.exists(berkas):
                os.unlink(berkas)


@router.get("/api/v1/recordings/{recording_id}/indices")
async def get_indices(
    recording_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_peneliti),
):
    from app.models.tables import AcousticIndex
    result = await db.execute(
        select(AcousticIndex)
        .join(Recording, Recording.id == AcousticIndex.recording_id)
        .where(AcousticIndex.recording_id == recording_id, recording_scope(current_user))
    )
    idx = result.scalar()
    if not idx:
        raise HTTPException(404, "Acoustic indices not computed yet")

    def angka(nilai):
        """Ubah NaN dan inf jadi null.

        json.dumps menolak nilai tidak berhingga dan melempar ValueError di
        tengah penyusunan respons, jadi klien menerima 500 tanpa header CORS dan
        browser melaporkannya sebagai galat CORS. Baris lama di database bisa
        masih berisi NaN dari audio sunyi sebelum worker diperbaiki.
        """
        if nilai is None:
            return None
        nilai = float(nilai)
        return nilai if math.isfinite(nilai) else None

    return {
        "recording_id": idx.recording_id,
        "aci": angka(idx.aci),
        "ndsi": angka(idx.ndsi),
        "adi": angka(idx.adi),
        "bi": angka(idx.bi),
        "computed_at": idx.computed_at.isoformat() if idx.computed_at else None,
        "caveat": "Indeks soundscape adalah indikator pelengkap, bukan proxy tunggal biodiversitas (paper #19).",
    }
