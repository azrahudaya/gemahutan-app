"""Pembaca audio streaming: hasilkan segmen beroverlap tanpa memuat file penuh.

Alasan: butir 7 (rekaman 60 menit hemat RAM). `librosa.load(audio_path)`
memuat seluruh berkas jadi satu array float32. Rekaman 60 menit @ 48 kHz
mono = 691 MB, dan karena cascade memanggil BirdNET + Track B + indeks
akustik, audio dimuat berkali-kali -> RAM tembus 3,9 GB.

Fungsi utama `segmen_stream` membaca satu jendela per waktu memakai
`soundfile.SoundFile.seek/read` (buffer kecil), lalu resample per jendela.
Berkas yang tidak didukung soundfile (mp3/aac/m4a) jatuh ke `librosa.load`
penuh -- tapi kasus itu jarang untuk audio rekaman GemaHutan.

Jalankan: python -m ml.engines.streaming <file>  untuk uji cepat.
"""
from __future__ import annotations

from collections.abc import Iterator

import numpy as np

SR_TARGET = 48000
SEGMENT_DURATION = 3.0
OVERLAP = 1.0


def _resample(y: np.ndarray, src_sr: int, dst_sr: int) -> np.ndarray:
    """Resample mono float32 ke dst_sr. Tanpa scipy, pakai numpy interp."""
    if src_sr == dst_sr:
        return y.astype(np.float32)
    try:
        from scipy.signal import resample_poly
        gcd = int(np.gcd(src_sr, dst_sr))
        up = dst_sr // gcd
        down = src_sr // gcd
        return resample_poly(y.astype(np.float64), up, down).astype(np.float32)
    except Exception:
        # Fallback: interpolasi linier sederhana.
        n_out = int(len(y) * dst_sr / src_sr)
        x_old = np.arange(len(y))
        x_new = np.linspace(0, len(y) - 1, n_out)
        return np.interp(x_new, x_old, y).astype(np.float32)


def _dapatkan_info(path: str):
    """Return (samplerate, total_frames, channels) via soundfile, atau None."""
    try:
        import soundfile as sf
        info = sf.info(path)
        return info.samplerate, info.frames, info.channels
    except Exception:
        return None


def durasi_audio(path: str) -> float:
    """Durasi total audio dalam detik. 0.0 kalau gagal membaca."""
    info = _dapatkan_info(path)
    if info is not None:
        return info[1] / info[0] if info[0] > 0 else 0.0
    try:
        import soundfile as sf
        with sf.SoundFile(path) as f:
            return f.frames / f.samplerate
    except Exception:
        try:
            import librosa
            return float(librosa.get_duration(path=path))
        except Exception:
            return 0.0


def segmen_stream(
    audio_path: str,
    sr: int = SR_TARGET,
    seg_dur: float = SEGMENT_DURATION,
    overlap: float = OVERLAP,
) -> Iterator[tuple[int, np.ndarray]]:
    """Yield (start_sample_padatan, segment) untuk tiap jendela beroverlap.

    start_sample_padatan: posisi awal jendela dalam domain 48 kHz (konsisten
    dengan hitungan librosa.load penuh). segment: array float32 48 kHz mono
    sepanjang seg_dur detik (di-pad kalau ujung).

    Jatuh ke full-load kalau format tidak dibaca soundfile.
    """
    info = _dapatkan_info(audio_path)
    if info is None:
        yield from _segmen_stream_librosa(audio_path, sr, seg_dur, overlap)
        return

    src_sr, total_frames, channels = info
    try:
        import soundfile as sf
    except Exception:
        yield from _segmen_stream_librosa(audio_path, sr, seg_dur, overlap)
        return

    seg_len_src = int(src_sr * seg_dur)
    step_src = int(src_sr * (seg_dur - overlap))
    seg_len_dst = int(sr * seg_dur)

    # Konversi total durasi ke domain target untuk hitungan start_sample.
    total_dst_frames = int(total_frames * sr / src_sr)

    with sf.SoundFile(audio_path) as f:
        start_src = 0
        start_dst = 0
        while start_src < total_frames:
            f.seek(start_src)
            # Baca mono. SoundFile.read selalu memberi shape (frames,) untuk mono.
            chunk = f.read(frames=seg_len_src, dtype="float32", always_2d=False)
            if channels > 1 and chunk.ndim == 2:
                chunk = chunk.mean(axis=1)

            if chunk.size < seg_len_src // 2:
                break

            seg = _resample(chunk, src_sr, sr)

            if len(seg) < seg_len_dst:
                seg = np.pad(seg, (0, seg_len_dst - len(seg)))
            else:
                seg = seg[:seg_len_dst]

            yield start_dst, seg.astype(np.float32)

            start_src += step_src
            start_dst += step_src * sr // src_sr

    # Handle sisa ujung yang mungkin terlewat karena pembulatan.
    _ = total_dst_frames  # total dipakai hanya untuk dokumentasi; tidak wajib.


def _segmen_stream_librosa(
    audio_path: str, sr: int, seg_dur: float, overlap: float
) -> Iterator[tuple[int, np.ndarray]]:
    """Fallback: muat penuh lalu potong. Perilaku lama, RAM besar."""
    import librosa
    y, sr_out = librosa.load(audio_path, sr=sr, mono=True)
    seg_len = int(sr * seg_dur)
    step = int(sr * (seg_dur - overlap))

    for start in range(0, len(y), step):
        seg = y[start:start + seg_len]
        if len(seg) < seg_len // 2:
            break
        if len(seg) < seg_len:
            seg = np.pad(seg, (0, seg_len - len(seg)))
        yield start, seg.astype(np.float32)


if __name__ == "__main__":
    import sys
    import time
    if len(sys.argv) < 2:
        print("Pakai: python -m ml.engines.streaming <file_audio>")
        sys.exit(1)

    path = sys.argv[1]
    t0 = time.time()
    n = 0
    total_dur = 0.0
    seg = None
    info = _dapatkan_info(path)
    if info:
        src_sr, frames, ch = info
        total_dur = frames / src_sr
    for _start_sample, _seg in segmen_stream(path):
        n += 1
    elapsed = time.time() - t0
    print(f"File: {path}")
    print(f"  Info: sr={info[0] if info else '?'}, dur={total_dur:.1f}s")
    print(f"  Segmen: {n}, waktu: {elapsed:.2f}s")
    print(f"  Segment pertama shape: {seg.shape}, dtype: {seg.dtype}")
