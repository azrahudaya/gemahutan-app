"""Ukur latensi dan memori inference pada rekaman panjang.

Menyambung klip demo menjadi 10 dan 60 menit, menjalankan CascadeEngine.predict
(jalur worker), lalu menulis ml/reports/latensi.json dengan waktu proses dan
peak RSS.

Jalankan: .venv/bin/python ml/ukur_latensi.py [--menit 60] [--cuma 10]

Kriteria C16: 60 menit < 900 detik, RSS < 1800 MB.
"""

from __future__ import annotations

import argparse
import json
import resource
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
ML_DIR = ROOT / "ml"
REPORTS = ML_DIR / "reports"
SR = 48000


def rss_mb() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0


def cari_klip_demo() -> list[Path]:
    kandidat = []
    for pat in ["ml/data/demo", "ml/data/audio", "demo"]:
        p = ROOT / pat
        if p.exists():
            kandidat.extend(sorted(p.rglob("*.mp3"))[:3])
            kandidat.extend(sorted(p.rglob("*.wav"))[:3])
    # Fallback: klip XC pertama yang ditemukan.
    if not kandidat:
        kandidat = sorted((ROOT / "ml/data/audio").rglob("*.mp3"))[:3]
    return kandidat


def sambung_klip(klip: list[Path], menit: float, sr: int = SR) -> np.ndarray:
    """Sambung klip berulang sampai mendekati target menit."""
    import librosa
    segmen = []
    total = 0.0
    target = int(menit * 60 * sr)
    i = 0
    while total < target:
        y, _ = librosa.load(str(klip[i % len(klip)]), sr=sr, mono=True)
        segmen.append(y)
        total += len(y)
        i += 1
    y = np.concatenate(segmen)[:target]
    return y.astype(np.float32)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--menit", type=int, default=60)
    ap.add_argument("--cuma-10", action="store_true", help="hanya benchmark 10 menit")
    args = ap.parse_args()

    from ml.engines.cascade import CascadeEngine
    engine = CascadeEngine()
    klip = cari_klip_demo()
    if not klip:
        print("Tidak ada klip demo.", file=sys.stderr)
        return 2
    print(f"Klip demo: {[str(k) for k in klip]}")

    hasil = {}
    menit_list = [10] if args.cuma_10 else [10, args.menit]
    for menit in menit_list:
        y = sambung_klip(klip, menit)
        durasi_s = len(y) / SR
        # Tulis audio sementara untuk engine (butuh path).
        tmp = ROOT / f"/tmp/gemahutan_{menit}m.wav"
        import soundfile as sf
        sf.write(str(tmp), y, SR)

        t0 = time.time()
        try:
            deteksi = engine.predict(str(tmp))
        except Exception as exc:
            print(f"  gagal {menit}m: {exc}", file=sys.stderr)
            continue
        t1 = time.time()
        rss_sesudah = rss_mb()

        hasil[f"{menit}m"] = {
            "durasi_audio_s": round(durasi_s, 1),
            "waktu_proses_s": round(t1 - t0, 1),
            "faktor_realtime": round((t1 - t0) / durasi_s, 2),
            "peak_rss_mb": round(rss_sesudah, 1),
            "n_deteksi": len(deteksi),
        }
        tmp.unlink(missing_ok=True)
        print(json.dumps({f"{menit}m": hasil[f"{menit}m"]}, ensure_ascii=False))

    # 60 menit jadi angka utama di latensi.json.
    kunci_60 = "60m" if "60m" in hasil else "10m"
    out = {
        "waktu_s": hasil[kunci_60]["waktu_proses_s"],
        "peak_rss_mb": hasil[kunci_60]["peak_rss_mb"],
        "durasi_audio_s": hasil[kunci_60]["durasi_audio_s"],
        "rincian": hasil,
        "dibuat": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "latensi.json").write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print(f"\nlatensi.json: {json.dumps(out, indent=2, ensure_ascii=False)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
