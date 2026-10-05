"""Uji W-34: WebM tanpa durasi (keluaran MediaRecorder Chrome) tetap diterima API."""

import shutil
import subprocess

import pytest

from app.routers.recordings import _durasi_format, _hitung_durasi
from helpers_uji import lokasi_pertama, ranger_baru


def webm_tanpa_durasi(detik: float = 3.0) -> bytes:
    """WebM opus tanpa durasi di header, meniru keluaran MediaRecorder Chrome.

    Flag `-live 1` membuat ffmpeg menulis WebM "live" yang tidak punya durasi
    di header, persis seperti rekaman dari peramban.
    """
    ffmpeg = shutil.which("ffmpeg")
    assert ffmpeg, "ffmpeg tidak tersedia di lingkungan test"
    hasil = subprocess.run(
        [
            ffmpeg,
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=440:duration={detik}",
            "-c:a",
            "libopus",
            "-f",
            "webm",
            "-live",
            "1",
            "-",
        ],
        capture_output=True,
        check=True,
        timeout=30,
    )
    return hasil.stdout


def test_durasi_format_kosong_atau_na():
    assert _durasi_format({"format": {}}) is None
    assert _durasi_format({"format": {"duration": "N/A"}}) is None
    assert _durasi_format({"format": {"duration": "3.0"}}) == 3.0


def test_hitung_durasi_webm_tanpa_durasi(tmp_path):
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        pytest.skip("ffmpeg tidak tersedia")
    jalur = tmp_path / "rekam.webm"
    jalur.write_bytes(webm_tanpa_durasi(3.0))
    durasi = _hitung_durasi(str(jalur), ffmpeg)
    assert durasi is not None
    assert 2.0 < durasi <= 3.2


# Peramban mengirim tipe lengkap dengan parameter codec dari recorder.mimeType.
@pytest.mark.parametrize("tipe", ["audio/webm", "audio/webm;codecs=opus", "audio/mp4;codecs=mp4a.40.2"])
async def test_unggah_webm_tanpa_durasi_diterima(client, tipe):
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg tidak tersedia")
    headers, _ = await ranger_baru(client)
    situs = await lokasi_pertama(client, headers)
    resp = await client.post(
        "/api/v1/recordings",
        headers=headers,
        files={"file": ("fase2-rekam-chrome.webm", webm_tanpa_durasi(), tipe)},
        data={"site_id": str(situs)},
    )
    assert resp.status_code == 201, resp.text
