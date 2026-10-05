"""Ukur waktu proses dan RSS Perch pada rekaman 60 menit (syarat K6 gaya C16).

Batas yang dipakai (ML_10 butir 3): lewat 4 GB RSS atau 900 detik = GAGAL
sumber daya. Baseline produksi untuk rekaman yang sama ada di
ml/reports/latensi.json: 94,6 detik dan 1134 MB.

DIUKUR DI CPU, dan itu bukan pilihan sembarangan. latensi.json menyebut mesin
server "Intel N100 4-core, 8 GB RAM, TensorFlow CPU" dan batas RAM 4 GB di
ML_10 adalah batas server. Mengukur Perch di GPU laptop akan memberi angka yang
tidak pernah dialami produksi, dan itu persis jenis angka optimistis palsu yang
sudah bikin masalah di putaran sebelumnya. CUDA dimatikan lewat
CUDA_VISIBLE_DEVICES="" sebelum TensorFlow diimpor.

Yang diukur hanya biaya EKSTRAKSI embedding, yaitu satu-satunya hal yang
berubah pada K6. Biaya kepala LR (perkalian matriks 1536x26) di bawah
seperseribu dari itu dan dicatat terpisah.

RSS diukur dari /proc/self/status VmHWM, yaitu high water mark proses ini,
bukan rata-rata, karena yang bisa membunuh server adalah puncaknya.

Jalankan: .venv-perch/bin/python3 ml/ukur_sumberdaya_perch.py
"""
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ML = REPO / "ml"

SR = 32000
DURASI = 5.0
PANJANG = int(SR * DURASI)
BATAS_RSS_MB = 4096
BATAS_WAKTU_S = 900


def vmhwm_mb() -> float:
    """Peak RSS proses ini dalam MB, dari VmHWM di /proc."""
    for baris in Path("/proc/self/status").read_text().splitlines():
        if baris.startswith("VmHWM:"):
            return int(baris.split()[1]) / 1024.0
    return -1.0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--audio", default=str(ML / "data" / "bench_60min.mp3"))
    ap.add_argument("--model-dir", default=str(ML / "models_perch"))
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--out", default=str(ML / "reports" / "k6_perch" / "sumberdaya.json"))
    ap.add_argument("--izinkan-gpu", action="store_true",
                    help="ukur di GPU. Angkanya TIDAK berlaku untuk server N100 yang CPU-saja, "
                         "dipakai hanya untuk melengkapi laporan setelah jalur CPU dibuktikan mati.")
    a = ap.parse_args()

    if not a.izinkan_gpu:
        os.environ["CUDA_VISIBLE_DEVICES"] = ""
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

    import numpy as np
    import tensorflow as tf

    gpu = tf.config.list_physical_devices("GPU")
    print("GPU terlihat:", gpu or "tidak ada (benar, diukur di CPU)")

    rss_awal = vmhwm_mb()

    t_muat0 = time.time()
    model = tf.saved_model.load(a.model_dir)
    fn = model.signatures["serving_default"]
    t_muat = time.time() - t_muat0
    rss_setelah_muat = vmhwm_mb()
    print(f"muat model: {t_muat:.1f}s, RSS puncak {rss_setelah_muat:.0f} MB")

    import librosa

    t_baca0 = time.time()
    y, _ = librosa.load(a.audio, sr=SR, mono=True)
    t_baca = time.time() - t_baca0
    durasi_audio = len(y) / SR
    print(f"audio: {durasi_audio:.0f}s ({durasi_audio / 60:.1f} menit), baca {t_baca:.1f}s")

    n_jendela = len(y) // PANJANG
    print(f"jendela 5 detik tanpa tumpang tindih: {n_jendela}")

    # Pemanasan satu batch supaya waktu kompilasi grafik tidak dihitung sebagai
    # biaya per jendela. Server pun hanya mengalaminya sekali per proses.
    _ = fn(tf.constant(y[:PANJANG * 1].reshape(1, -1).astype(np.float32)))
    rss_setelah_panas = vmhwm_mb()

    t0 = time.time()
    n_proses = 0
    for s in range(0, n_jendela * PANJANG, PANJANG * a.batch):
        blok = y[s: s + PANJANG * a.batch]
        n = len(blok) // PANJANG
        if n == 0:
            break
        batch = blok[: n * PANJANG].reshape(n, PANJANG).astype(np.float32)
        _ = fn(tf.constant(batch))
        n_proses += n
    t_proses = time.time() - t0
    rss_puncak = vmhwm_mb()

    total = t_muat + t_baca + t_proses
    hasil = {
        "audio": str(Path(a.audio).name),
        "durasi_audio_s": round(durasi_audio, 1),
        "perangkat": "GPU" if a.izinkan_gpu else "CPU (CUDA_VISIBLE_DEVICES kosong)",
        "n_jendela": n_proses,
        "batch": a.batch,
        "waktu_muat_model_s": round(t_muat, 1),
        "waktu_baca_audio_s": round(t_baca, 1),
        "waktu_embedding_s": round(t_proses, 1),
        "waktu_total_s": round(total, 1),
        "faktor_realtime": round(total / durasi_audio, 3),
        "rss_awal_mb": round(rss_awal, 0),
        "rss_setelah_muat_mb": round(rss_setelah_muat, 0),
        "rss_setelah_pemanasan_mb": round(rss_setelah_panas, 0),
        "rss_puncak_mb": round(rss_puncak, 0),
        "batas_rss_mb": BATAS_RSS_MB,
        "batas_waktu_s": BATAS_WAKTU_S,
        "lulus_rss": bool(rss_puncak < BATAS_RSS_MB),
        "lulus_waktu": bool(total < BATAS_WAKTU_S),
    }
    hasil["lulus_sumberdaya"] = bool(hasil["lulus_rss"] and hasil["lulus_waktu"])
    hasil["baseline_produksi"] = {
        "waktu_s": 94.6,
        "rss_maks_mb": 1134,
        "sumber": "ml/reports/latensi.json",
    }

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(hasil, indent=2, ensure_ascii=False))
    print(json.dumps(hasil, indent=2, ensure_ascii=False))
    print("\nSUMBER DAYA:", "LULUS" if hasil["lulus_sumberdaya"] else "GAGAL")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
