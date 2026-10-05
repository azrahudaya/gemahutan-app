"""Uji independen: 131 klip dari negara lain, TANPA memakai label.

Memakai checkpoint produksi (ml/checkpoints/) lewat EmbeddingClassifierEngine
(jalur produksi). Pemilihan jendela terbaik = jendela dengan probabilitas
maksimum di antara 25 kelas target (tanpa `_negative`), TANPA melihat label.

Output mengikuti skema C09:
  ml/reports/uji_independen.json

Jalankan: python3 ml/uji_independen.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

ML_DIR = ROOT / "ml"
INDEP_DIR = ML_DIR / "data" / "uji_independen"
INDEP_CACHE = INDEP_DIR / "embedding_cache"
INDEP_MANIFEST = INDEP_DIR / "manifest.csv"
CHECKPOINT = ML_DIR / "checkpoints"
REPORTS = ML_DIR / "reports"


def f1_macro(y_true, y_pred, n_classes):
    f1s = []
    for k in range(n_classes):
        tp = np.sum((y_pred == k) & (y_true == k))
        fp = np.sum((y_pred == k) & (y_true != k))
        fn = np.sum((y_pred != k) & (y_true == k))
        f1 = 2 * tp / (2 * tp + fp + fn) if (2 * tp + fp + fn) > 0 else 0.0
        f1s.append(f1)
    return float(np.mean(f1s))


def bootstrap_ci_acc(correct: np.ndarray, n_bootstrap: int = 2000) -> list[float]:
    """CI95 bootstrap untuk akurasi, sampel klip."""
    rng = np.random.default_rng(42)
    means = []
    n = len(correct)
    for _ in range(n_bootstrap):
        idx = rng.choice(n, size=n, replace=True)
        means.append(float(np.mean(correct[idx])))
    means.sort()
    return [round(float(means[int(0.025 * n_bootstrap)]), 4),
            round(float(means[int(0.975 * n_bootstrap)]), 4)]


def muat_engine(ckpt_dir: Path, emb_dir: Path):
    """Muat EmbeddingClassifierEngine dengan direktori model tertentu.

    Kenapa konstanta modul ditimpa, bukan cuma os.environ: embedding_clf membaca
    GEMAHUTAN_CHECKPOINT_DIR dan GEMAHUTAN_EMB_DIR SEKALI saat impor, menjadi
    konstanta tingkat modul (baris 11-12). Menyetel environ SETELAH impor tidak
    berpengaruh apa pun, dan kegagalannya SENYAP: engine tetap memuat checkpoint
    produksi sambil skrip mencetak direktori kandidat yang diminta. Dibuktikan
    dengan menunjuk --checkpoint-dir ke direktori yang tidak ada: tidak ada
    error, mean tetap 1024 dimensi dari ml/checkpoints.

    environ tetap di-set untuk proses anak atau modul yang belum diimpor.
    """
    os.environ["GEMAHUTAN_CHECKPOINT_DIR"] = str(ckpt_dir)
    os.environ["GEMAHUTAN_EMB_DIR"] = str(emb_dir)

    from ml.engines import embedding_clf as _mod
    from ml.engines.embedding_clf import EmbeddingClassifierEngine

    _mod.CHECKPOINT_DIR = Path(ckpt_dir)
    _mod.EMB_DIR = Path(emb_dir)
    if not (Path(ckpt_dir) / "best_model.npz").exists():
        raise SystemExit(f"ERROR: best_model.npz tidak ada di {ckpt_dir}")

    engine = EmbeddingClassifierEngine.__new__(EmbeddingClassifierEngine)
    EmbeddingClassifierEngine.__init__(engine)
    engine._load_birdnet_interpreter = lambda: None
    engine._ensure_loaded()
    return engine


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint-dir", default=str(CHECKPOINT),
                    help="direktori checkpoint (best_model.npz, normalization.npz)")
    ap.add_argument("--emb-dir", default=str(ML_DIR / "embeddings"),
                    help="direktori embedding untuk label_map")
    ap.add_argument("--out-json", default=str(REPORTS / "uji_independen.json"),
                    help="lokasi output JSON")
    # Bawaannya SAMA dengan perilaku lama (INDEP_CACHE), jadi angka baseline
    # tidak berubah. Argumen ini hanya supaya kandidat yang memakai resep
    # embedding berbeda (mis. K3 jendela bersuara) bisa dinilai lewat jalur
    # ukur yang sama persis, bukan lewat skrip tandingan.
    ap.add_argument("--cache-dir", default=str(INDEP_CACHE),
                    help="direktori cache embedding per klip (.npy)")
    args = ap.parse_args()

    ckpt_dir = Path(args.checkpoint_dir)
    emb_dir = Path(args.emb_dir)
    out_json = Path(args.out_json)
    cache_dir = Path(args.cache_dir)

    if not cache_dir.exists():
        print(f"ERROR: cache embedding tidak ditemukan: {cache_dir}")
        return 1

    print(f"Memuat checkpoint: {ckpt_dir}")
    engine = muat_engine(ckpt_dir, emb_dir)
    label_map = engine._label_map
    if label_map is None:
        print("ERROR: label_map tidak termuat dari model")
        return 1
    n_kelas = len(label_map)

    pool_ids = sorted(p.stem for p in cache_dir.glob("*.npy"))
    pool_sha = hashlib.sha256("\n".join(pool_ids).encode("utf-8")).hexdigest()
    print(f"Pool independen: {len(pool_ids)} klip, sha256 {pool_sha}")

    # Daftar kelas target (tanpa _negative)
    neg_idx = label_map.get("_negative", -1)
    target_kelas = [k for k in range(n_kelas) if k != neg_idx]
    print(f"Kelas target (tanpa _negative): {len(target_kelas)}")

    # sha256 checkpoint dari direktori model yang sedang dinilai
    ckpt_file = ckpt_dir / "best_model.npz"
    if not ckpt_file.exists():
        print(f"ERROR: checkpoint tidak ditemukan: {ckpt_file}")
        return 1
    sha256_ckpt = hashlib.sha256(ckpt_file.read_bytes()).hexdigest()

    # Muat manifest uji independen
    manifest_indep = {}
    with open(INDEP_MANIFEST) as f:
        for line in f.readlines()[1:]:
            parts = line.strip().split(",")
            cid = parts[0].strip()
            sp = parts[4].strip()
            manifest_indep[cid] = sp

    npy_files = sorted(cache_dir.glob("*.npy"))
    print(f"Berkas .npy: {len(npy_files)}")

    hasil_terbaik = []
    hasil_semua = []

    for npy_path in npy_files:
        clip_id = npy_path.stem
        sp = manifest_indep.get(clip_id)
        if sp is None or sp not in label_map:
            continue
        target = label_map[sp]

        embs = np.load(npy_path).astype(np.float32)
        n_windows = embs.shape[0]
        if n_windows == 0:
            continue

        # Normalisasi + probabilitas terkalibrasi lewat engine
        x_norm = ((embs - engine._mean) / engine._std).astype(np.float32)
        probs = engine._calibrated_probs(x_norm)  # [n_windows, n_kelas]

        # Semua jendela: tiap jendela prediksi sendiri
        for w in range(n_windows):
            pred_w = int(np.argmax(probs[w]))
            hasil_semua.append({"clip_id": clip_id, "window": w,
                                 "target": int(target), "pred": pred_w,
                                 "correct": pred_w == target})

        # Jendela terbaik: probabilitas maksimum di antara 25 kelas target,
        # TANPA melihat label asli klip.
        max_probs = probs[:, target_kelas].max(axis=1)
        best_w = int(np.argmax(max_probs))
        best_pred = int(np.argmax(probs[best_w]))
        hasil_terbaik.append({"clip_id": clip_id,
                               "target": int(target), "pred": best_pred,
                               "correct": best_pred == target})

    n_best = len(hasil_terbaik)
    n_semua = len(hasil_semua)

    y_best = np.array([h["target"] for h in hasil_terbaik])
    p_best = np.array([h["pred"] for h in hasil_terbaik])
    correct_best = np.array([h["correct"] for h in hasil_terbaik])

    acc_best = float(np.mean(correct_best))
    f1_best = f1_macro(y_best, p_best, n_kelas)
    ci95_acc = bootstrap_ci_acc(correct_best)

    y_semua = np.array([h["target"] for h in hasil_semua])
    p_semua = np.array([h["pred"] for h in hasil_semua])
    acc_semua = float(np.mean([h["correct"] for h in hasil_semua]))
    f1_semua = f1_macro(y_semua, p_semua, n_kelas)

    print(f"\nJendela terbaik ({n_best} klip, tanpa label):")
    print(f"  Acc: {acc_best:.4f} (CI95 {ci95_acc})")
    print(f"  F1:  {f1_best:.4f}")
    print(f"\nSemua jendela ({n_semua} jendela):")
    print(f"  Acc: {acc_semua:.4f}")
    print(f"  F1:  {f1_semua:.4f}")

    # Simpan sesuai skema
    out_json.parent.mkdir(parents=True, exist_ok=True)
    output = {
        "model": "produksi",
        "sha256_checkpoint": sha256_ckpt,
        "pool": {
            "n_klip": len(pool_ids),
            "sha256_clip_ids": pool_sha,
        },
        "metode_pemilihan_jendela": "tanpa_label",
        "jendela_terbaik": {
            "acc": round(acc_best, 4),
            "f1_macro": round(f1_best, 4),
            "ci95_acc": ci95_acc,
        },
        "semua_jendela": {
            "acc": round(acc_semua, 4),
            "f1_macro": round(f1_semua, 4),
        },
        "n_klip": n_best,
        "kandidat": [],
    }
    out_json.write_text(json.dumps(output, indent=2, ensure_ascii=False))
    print(f"\nOutput: {out_json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())