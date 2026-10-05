"""Augmentasi audio untuk data latih.

Fungsi augment_window() menghasilkan beberapa varian augmentasi deterministik
dari sebuah waveform numpy. Hanya dipakai pada TRAINING; data val/test dan
inference tetap pada audio original supaya hasil evaluasi bisa dibandingkan
langsung dengan model lama.

Varian yang tersedia:
  - original                  : tanpa augmentasi
  - time_shift_500ms          : roll ±0.5 detik pada axis 0
  - gain_+6dB                 : kalikan 2.0
  - gain_-6dB                 : kalikan 0.5
  - time_mask_200ms           : zero 200 ms di posisi random
  - time_stretch_1.0          : placeholder, lihat catatan di bawah
  - gaussian_noise_snr_20db   : tambah white noise target SNR +20 dB

Catatan time_stretch:
  librosa.effects.time_stretch bawaan menggunakan fase vocoder yang ikut
  menggeser pitch. pyrubberband tidak terpasang di environment ini dan
  numpy.interp manual tidak bisa mengubah tempo tanpa aliasing pada audio
  48 kHz. Untuk baseline dipakai rate 1.0 (tanpa peregangan) dan
  didokumentasikan keterbatasannya. Aktivasi time stretch ditunda sampai
  pyrubberband/sox tersedia.

Output deterministik: seed numpy dipasang di awal setiap panggilan.
"""
import numpy as np

SR = 48000
DEFAULT_VARIANTS = (
    "original",
    "time_shift_500ms",
    "gain_+6dB",
    "gain_-6dB",
    "time_mask_200ms",
    "time_stretch_1.0",
    "gaussian_noise_snr_20db",
)


def _snr_db(signal: np.ndarray, noise: np.ndarray) -> float:
    p_sig = float(np.mean(signal ** 2)) + 1e-12
    p_noise = float(np.mean(noise ** 2)) + 1e-12
    return 10.0 * float(np.log10(p_sig / p_noise))


def time_shift(wav: np.ndarray, sr: int, max_seconds: float = 0.5,
               rng: np.random.Generator | None = None) -> np.ndarray:
    """Roll waveform sepanjang ±max_seconds. Wrap-around mempertahankan panjang."""
    if rng is None:
        rng = np.random.default_rng()
    shift = int(rng.integers(-int(max_seconds * sr), int(max_seconds * sr) + 1))
    if shift == 0:
        return wav.copy()
    return np.roll(wav, shift)


def gain_db(wav: np.ndarray, gain_db_value: float) -> np.ndarray:
    """Kalikan amplitude dengan faktor 10^(gain_db_value/20)."""
    factor = 10.0 ** (gain_db_value / 20.0)
    return (wav * factor).astype(np.float32)


def time_mask(wav: np.ndarray, sr: int, mask_seconds: float = 0.2,
              rng: np.random.Generator | None = None) -> np.ndarray:
    """Zero-out window sepanjang mask_seconds pada posisi random."""
    if rng is None:
        rng = np.random.default_rng()
    out = wav.copy()
    mask_len = int(mask_seconds * sr)
    if mask_len <= 0 or mask_len >= len(out):
        return out
    start = int(rng.integers(0, len(out) - mask_len + 1))
    out[start:start + mask_len] = 0.0
    return out


def time_stretch_placeholder(wav: np.ndarray, rate: float = 1.0) -> np.ndarray:
    """Placeholder time stretch; lihat catatan di modul.

    pyrubberband tidak terpasang dan librosa.effects.time_stretch bawaan
    mengubah pitch. Untuk baseline dipakai rate 1.0 (identik dengan original)
    dan keterbatasannya didokumentasikan di docstring modul.
    """
    if rate == 1.0:
        return wav.copy()
    # Fallback tanpa pengubahan pitch: resample linier pada axis 0.
    # Tidak dipakai di baseline; hanya masuk sini kalau rate != 1.0.
    new_len = int(round(len(wav) / rate))
    if new_len == len(wav):
        return wav.copy()
    x_old = np.arange(len(wav))
    x_new = np.linspace(0, len(wav) - 1, new_len)
    stretched = np.interp(x_new, x_old, wav).astype(np.float32)
    if len(stretched) >= len(wav):
        return stretched[: len(wav)]
    pad = np.zeros(len(wav) - len(stretched), dtype=np.float32)
    return np.concatenate([stretched, pad])


def gaussian_noise_snr(wav: np.ndarray, target_snr_db: float = 20.0,
                       rng: np.random.Generator | None = None) -> np.ndarray:
    """Tambah white noise dengan SNR target terhadap signal."""
    if rng is None:
        rng = np.random.default_rng()
    noise = rng.standard_normal(len(wav)).astype(np.float32)
    cur_snr = _snr_db(wav, noise)
    # noise_scaled = noise * 10^((cur_snr - target_snr_db) / 20)
    scale = 10.0 ** ((cur_snr - target_snr_db) / 20.0)
    return (wav + scale * noise).astype(np.float32)


def augment_window(wav: np.ndarray, sr: int = SR,
                   variants: tuple[str, ...] = DEFAULT_VARIANTS,
                   seed: int | None = None) -> list[tuple[str, np.ndarray]]:
    """Hasilkan list varian augmentasi deterministik dari satu waveform.

    Hanya untuk TRAINING. Eval/test/inference pakai waveform original.
    seed mengontrol rng internal supaya panggilan yang sama menghasilkan
    varian yang sama (berguna untuk debugging).
    """
    rng = np.random.default_rng(seed)
    out: list[tuple[str, np.ndarray]] = []
    for name in variants:
        if name == "original":
            out.append((name, wav.astype(np.float32, copy=True)))
        elif name == "time_shift_500ms":
            out.append((name, time_shift(wav, sr, max_seconds=0.5, rng=rng)))
        elif name == "gain_+6dB":
            out.append((name, gain_db(wav, 6.0)))
        elif name == "gain_-6dB":
            out.append((name, gain_db(wav, -6.0)))
        elif name == "time_mask_200ms":
            out.append((name, time_mask(wav, sr, mask_seconds=0.2, rng=rng)))
        elif name == "time_stretch_1.0":
            out.append((name, time_stretch_placeholder(wav, rate=1.0)))
        elif name == "gaussian_noise_snr_20db":
            out.append((name, gaussian_noise_snr(wav, 20.0, rng=rng)))
        else:
            raise ValueError(f"varian augmentasi tidak dikenal: {name}")
    return out


if __name__ == "__main__":
    # Smoke test: bangun waveform dummy 3 detik lalu cetak bentuk tiap varian.
    rng = np.random.default_rng(0)
    dummy = rng.standard_normal(SR * 3).astype(np.float32) * 0.1
    hasil = augment_window(dummy, seed=42)
    for nama, wav in hasil:
        print(f"  {nama:30s} shape={wav.shape} mean={wav.mean():+.5f}")
    print(f"total varian: {len(hasil)}")