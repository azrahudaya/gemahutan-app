"""Test indeks akustik: nilai tidak berhingga tidak boleh lolos.

Bug yang dijaga di sini: audio sunyi membuat ACI, NDSI, dan BI bernilai NaN,
bukan melempar galat. Nilai itu dulu tersimpan ke database, lalu endpoint
/api/v1/recordings/{id}/indices menjawab 500 karena json.dumps menolak NaN.
Di browser gejalanya tampak seperti galat CORS, jadi penyebab aslinya mudah
salah dibaca. Test ini memastikan worker mengembalikan None untuk audio yang
tidak bermakna dan nilai berhingga untuk audio normal.
"""
import wave

import numpy as np
import pytest


def _tulis_wav(path, data, fs=22050):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(fs)
        w.writeframes((np.clip(data, -1, 1) * 32767).astype("<i2").tobytes())


@pytest.fixture(scope="module")
def berkas_audio(tmp_path_factory):
    d = tmp_path_factory.mktemp("indeks")
    rng = np.random.default_rng(0)
    fs = 22050
    dibuat = {
        "sunyi": d / "sunyi.wav",
        "sunyi_pendek": d / "sunyi_pendek.wav",
        "derau": d / "derau.wav",
        "sinus": d / "sinus.wav",
    }
    _tulis_wav(dibuat["sunyi"], np.zeros(fs, dtype=np.float32))
    _tulis_wav(dibuat["sunyi_pendek"], np.zeros(int(fs * 0.4), dtype=np.float32))
    _tulis_wav(dibuat["derau"], rng.normal(0, 0.05, fs).astype(np.float32))
    _tulis_wav(dibuat["sinus"], (0.3 * np.sin(2 * np.pi * 3000 * np.arange(fs) / fs)).astype(np.float32))
    return dibuat


def test_audio_sunyi_tidak_menghasilkan_nan(berkas_audio):
    import worker

    for nama in ("sunyi", "sunyi_pendek"):
        out, _ = worker.compute_acoustic_indices(str(berkas_audio[nama]))
        assert all(v is None for v in out.values()), f"{nama}: {out}"


def test_audio_sunyi_memberi_catatan(berkas_audio):
    import worker

    _, note = worker.compute_acoustic_indices(str(berkas_audio["sunyi"]))
    assert note is not None and "sunyi" in note.lower()


def test_audio_normal_semua_berhingga(berkas_audio):
    import worker

    for nama in ("derau", "sinus"):
        out, note = worker.compute_acoustic_indices(str(berkas_audio[nama]))
        assert note is None, f"{nama}: catatan tak terduga {note}"
        assert out["aci"] is not None and out["ndsi"] is not None
        for kunci, nilai in out.items():
            assert nilai is not None, f"{nama}.{kunci} kosong"
            assert np.isfinite(nilai), f"{nama}.{kunci} tidak berhingga: {nilai}"
