"""Test bagian worker dan penyaring deteksi.

Dijalankan di dalam image worker: `make test-worker`. Yang diuji di sini adalah
logika yang sebelumnya tidak punya test sama sekali, yaitu konversi format audio
dan penyaring deteksi lemah di engine cascade.
"""
import subprocess

import pytest


@pytest.fixture(scope="module")
def berkas_uji(tmp_path_factory):
    """Satu wav pendek dan versi m4a-nya, dibuat dengan ffmpeg."""
    folder = tmp_path_factory.mktemp("audio")
    wav = folder / "contoh.wav"
    subprocess.run(
        ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "lavfi",
         "-i", "sine=frequency=440:duration=2", "-ar", "48000", "-ac", "1", str(wav)],
        check=True,
    )
    m4a = folder / "contoh.m4a"
    subprocess.run(
        ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(wav),
         "-c:a", "aac", str(m4a)],
        check=True,
    )
    return wav, m4a


def test_format_yang_didukung_dilewatkan(berkas_uji):
    """wav tidak perlu dikonversi, jalur yang sama dikembalikan."""
    import worker

    wav, _ = berkas_uji
    assert worker.siapkan_audio(wav) == wav


def test_m4a_dikonversi_ke_wav(berkas_uji):
    """librosa tidak membaca AAC, jadi m4a harus dikonversi dulu."""
    import worker

    _, m4a = berkas_uji
    hasil = worker.siapkan_audio(m4a)
    assert hasil != m4a
    assert hasil.suffix == ".wav"
    assert hasil.exists()
    assert hasil.stat().st_size > 0

    # Hasil konversi harus benar-benar bisa dibaca librosa.
    import librosa

    y, sr = librosa.load(str(hasil), sr=None, mono=True)
    assert sr == 48000
    assert len(y) > 0


def test_batas_percobaan_terbaca_dari_env(monkeypatch):
    import importlib

    monkeypatch.setenv("MAX_JOB_ATTEMPTS", "5")
    import worker

    assert importlib.reload(worker).MAX_ATTEMPTS == 5
    monkeypatch.delenv("MAX_JOB_ATTEMPTS", raising=False)
    assert importlib.reload(worker).MAX_ATTEMPTS == 3


def test_ambang_per_spesies_termuat():
    import worker

    ambang = worker._load_thresholds()
    assert "Aegithina tiphia" in ambang
    assert 0 < ambang["Aegithina tiphia"] <= 1


def _deteksi(spesies: str, conf: float, mulai: float, akhir: float):
    from ml.engines.base import DetectionResult

    return DetectionResult(
        species_scientific=spesies,
        species_common=spesies,
        confidence=conf,
        start_s=mulai,
        end_s=akhir,
        engine="uji",
        engine_version="0",
    )


def test_penyaring_buang_deteksi_pendek():
    """Potongan di bawah satu detik dibuang: itu bocoran energi, bukan nyanyian."""
    from ml.engines.cascade import CascadeEngine

    eng = CascadeEngine()
    hasil = eng._buang_deteksi_lemah([_deteksi("Gallus gallus", 0.9, 0.0, 0.4)])
    assert hasil == []


def test_penyaring_simpan_deteksi_kuat_dan_panjang():
    from ml.engines.cascade import CascadeEngine

    eng = CascadeEngine()
    hasil = eng._buang_deteksi_lemah([_deteksi("Gallus gallus", 0.8, 0.0, 3.0)])
    assert len(hasil) == 1


def test_penyaring_buang_yang_lemah_dan_muncul_sekali():
    """Keyakinan di bawah 0,5 harus muncul berulang supaya dianggap deteksi."""
    from ml.engines.cascade import CascadeEngine

    eng = CascadeEngine()
    sekali = [_deteksi("Pycnonotus goiavier", 0.3, 0.0, 3.0)]
    assert eng._buang_deteksi_lemah(sekali) == []

    berulang = [
        _deteksi("Pycnonotus goiavier", 0.3, 0.0, 3.0),
        _deteksi("Pycnonotus goiavier", 0.35, 3.0, 6.0),
    ]
    assert len(eng._buang_deteksi_lemah(berulang)) == 2


def test_penyaring_tidak_membuang_spesies_lain():
    """Penyaring berlaku per spesies, bukan menghapus seluruh rekaman."""
    from ml.engines.cascade import CascadeEngine

    eng = CascadeEngine()
    campuran = [
        _deteksi("Pycnonotus goiavier", 0.3, 0.0, 3.0),
        _deteksi("Gallus gallus", 0.9, 3.0, 6.0),
    ]
    hasil = eng._buang_deteksi_lemah(campuran)
    assert [d.species_scientific for d in hasil] == ["Gallus gallus"]
