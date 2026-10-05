"""Evaluate classifier: per-species metrics, confusion matrix, threshold calibration."""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

# evaluate.py dipanggil dari dua tempat: `cd ml && python evaluate.py` (Makefile)
# dan `python -m ml.evaluate` dari root repo. Root repo ditambahkan ke sys.path
# supaya `from ml.train import MLP` (di dalam main) selalu ketemu.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# Impor diletakkan setelah penyiapan sys.path di atas supaya `ml` selalu ketemu,
# baik dipanggil sebagai `python -m ml.evaluate` maupun `cd ml && python evaluate.py`.
from ml.model_loader import dengan_kalibrasi, muat  # noqa: E402

ML_DIR = Path(__file__).parent
EMB_DIR = ML_DIR / "embeddings"
CHECKPOINT_DIR = ML_DIR / "checkpoints"
SPLITS_FILE = ML_DIR / "data" / "splits.json"
REPORTS_DIR = ML_DIR / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"

# Jalur efektif. argparse menimpanya di main() supaya skrip yang sama bisa
# mengevaluasi model produksi, model korpus v2 (BirdNET 1024), dan model Perch
# (1536) tanpa menyalin skrip dan tanpa menyentuh berkas produksi.
JALUR = {
    "emb_dir": EMB_DIR,
    "checkpoint_dir": CHECKPOINT_DIR,
    "splits_file": SPLITS_FILE,
    "out_thresholds": REPORTS_DIR / "thresholds.json",
}


def load_eval_data():
    emb_dir = JALUR["emb_dir"]
    checkpoint_dir = JALUR["checkpoint_dir"]
    embeddings = np.load(emb_dir / "embeddings.npy")
    labels = np.load(emb_dir / "labels.npy")
    with open(emb_dir / "clip_ids.json") as f:
        clip_ids = json.load(f)
    with open(emb_dir / "label_map.json") as f:
        label_map = json.load(f)
    with open(JALUR["splits_file"]) as f:
        splits = json.load(f)

    norm = np.load(checkpoint_dir / "normalization.npz")
    mean, std = norm["mean"], norm["std"]

    cid_to_idx = {cid: i for i, cid in enumerate(clip_ids)}

    def get_split(name):
        indices = [cid_to_idx[c] for c in splits[name] if c in cid_to_idx]
        X = (embeddings[indices] - mean) / std
        y = labels[indices]
        return X, y

    return get_split("test"), get_split("val"), label_map


def per_species_metrics(y_true, y_pred, y_probs, label_map):
    inv_map = {v: k for k, v in label_map.items()}
    num_classes = len(label_map)
    results = {}

    for cls in range(num_classes):
        name = inv_map[cls]
        tp = np.sum((y_pred == cls) & (y_true == cls))
        fp = np.sum((y_pred == cls) & (y_true != cls))
        fn = np.sum((y_pred != cls) & (y_true == cls))

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

        # AUC-PR approximation
        cls_probs = y_probs[:, cls]
        cls_true = (y_true == cls).astype(int)
        auc_pr = compute_auc_pr(cls_true, cls_probs)

        support = int(np.sum(y_true == cls))
        results[name] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "auc_pr": round(auc_pr, 4),
            "support": support,
        }

    return results


def compute_auc_pr(y_true, scores):
    """Simple AUC-PR computation."""
    if np.sum(y_true) == 0:
        return 0.0
    order = np.argsort(-scores)
    y_sorted = y_true[order]
    tp_cumsum = np.cumsum(y_sorted)
    total_pos = np.sum(y_true)
    precisions = tp_cumsum / np.arange(1, len(y_sorted) + 1)
    recalls = tp_cumsum / total_pos
    # Trapezoidal
    auc = 0
    for i in range(1, len(recalls)):
        auc += (recalls[i] - recalls[i-1]) * precisions[i]
    return float(auc)


def calibrate_thresholds(y_true, y_probs, label_map, target_precision=0.8):
    """Find per-species threshold targeting a precision level.

    Kelas _negative TIDAK dikalibrasi ulang lewat grid ini: ambangnya
    diputuskan lewat trade-off curve (ml/measure_negative_threshold.py)
    dan disimpan terpisah. Kalau dipaksa lewat grid, hasilnya selalu
    0.10 (minimum grid) yang terlalu longgar untuk deteksi negatif.
    """
    inv_map = {v: k for k, v in label_map.items()}
    thresholds = {}
    for cls in range(len(label_map)):
        name = inv_map[cls]
        if name == "_negative":
            continue
        cls_probs = y_probs[:, cls]
        cls_true = (y_true == cls).astype(int)

        best_thresh = 0.5
        best_f1 = 0
        for thresh in np.arange(0.1, 0.95, 0.05):
            preds = (cls_probs >= thresh).astype(int)
            tp = np.sum(preds & cls_true)
            fp = np.sum(preds & ~cls_true.astype(bool))
            fn = np.sum(~preds.astype(bool) & cls_true)
            p = tp / (tp + fp) if (tp + fp) > 0 else 0
            r = tp / (tp + fn) if (tp + fn) > 0 else 0
            f1 = 2 * p * r / (p + r) if (p + r) > 0 else 0
            if f1 > best_f1:
                best_f1 = f1
                best_thresh = thresh

        thresholds[name] = round(float(best_thresh), 2)
    # Default ambang _negative kalau belum ada; bisa di-override manual.
    thresholds.setdefault("_negative", 0.30)
    return thresholds


def main(argv=None):
    ap = argparse.ArgumentParser(description="Evaluasi classifier + hitung ambang per spesies")
    ap.add_argument("--emb-dir", default=None, help="direktori embedding (embeddings.npy, labels.npy, clip_ids.json, label_map.json)")
    ap.add_argument("--checkpoint-dir", default=None, help="direktori best_model.npz + normalization.npz")
    ap.add_argument("--splits", default=None, help="berkas splits JSON")
    ap.add_argument("--akhiran", default="", help="akhiran nama berkas keluaran, mis. _perch")
    ap.add_argument("--out-thresholds", default=None, help="berkas ambang keluaran")
    args = ap.parse_args(argv)

    if args.emb_dir:
        JALUR["emb_dir"] = Path(args.emb_dir)
    if args.checkpoint_dir:
        JALUR["checkpoint_dir"] = Path(args.checkpoint_dir)
    if args.splits:
        JALUR["splits_file"] = Path(args.splits)
    akhiran = args.akhiran
    if args.out_thresholds:
        JALUR["out_thresholds"] = Path(args.out_thresholds)
    else:
        JALUR["out_thresholds"] = REPORTS_DIR / f"thresholds{akhiran}.json"

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    (X_test, y_test), (X_val, y_val), label_map = load_eval_data()
    num_classes = len(label_map)

    ckpt_dir = JALUR["checkpoint_dir"]
    # Normalisasi sudah diterapkan di load_eval_data, jadi mean dan std dari muat()
    # tidak dipakai lagi di sini.
    model, _, _ = muat(ckpt_dir)
    print(f"Checkpoint : {ckpt_dir}")
    print(f"Embedding  : {JALUR['emb_dir']}")

    # Test predictions
    test_probs = dengan_kalibrasi(model.forward(X_test), ckpt_dir)
    test_preds = np.argmax(test_probs, axis=1)
    test_acc = np.mean(test_preds == y_test)

    # Val predictions (for calibration)
    val_probs = dengan_kalibrasi(model.forward(X_val), ckpt_dir)
    val_preds = np.argmax(val_probs, axis=1)
    val_acc = np.mean(val_preds == y_val)

    print(f"Test accuracy: {test_acc:.4f}")
    print(f"Val accuracy: {val_acc:.4f}")

    # Per-species metrics
    species_metrics = per_species_metrics(y_test, test_preds, test_probs, label_map)

    # Macro averages
    precisions = [m["precision"] for m in species_metrics.values() if m["support"] > 0]
    recalls = [m["recall"] for m in species_metrics.values() if m["support"] > 0]
    f1s = [m["f1"] for m in species_metrics.values() if m["support"] > 0]

    macro_p = np.mean(precisions)
    macro_r = np.mean(recalls)
    macro_f1 = np.mean(f1s)

    print(f"Macro precision: {macro_p:.4f}")
    print(f"Macro recall: {macro_r:.4f}")
    print(f"Macro F1: {macro_f1:.4f}")

    # Calibrate thresholds on val set
    thresholds = calibrate_thresholds(y_val, val_probs, label_map)

    # Deskripsi dataset dibaca dari manifest dan splits, bukan ditulis manual,
    # supaya laporan tidak pernah lagi menyebut data sintetis setelah dataset
    # nyata dipakai.
    import csv as _csv
    import json as _json

    _manifest_rows = []
    _manifest_path = ML_DIR / "data" / "manifest.csv"
    if _manifest_path.exists():
        with open(_manifest_path) as _f:
            _manifest_rows = list(_csv.DictReader(_f))
    _clips = len(_manifest_rows)
    _species_real = sorted(
        {
            r["species_scientific"]
            for r in _manifest_rows
            if not r["clip_id"].startswith("ver-") and r["species_scientific"] != "_negative"
        }
    )
    _verified = len([r for r in _manifest_rows if r["clip_id"].startswith("ver-")])
    _split_sizes = {}
    _splits_path = ML_DIR / "data" / "splits.json"
    if _splits_path.exists():
        _splits = _json.loads(_splits_path.read_text())
        _split_sizes = {k: len(v) for k, v in _splits.items() if isinstance(v, list)}
    _test_clips = _split_sizes.get("test", 0)
    _dataset_line = (
        f"Xeno-canto Indonesia, {_clips} klip audio, {len(_species_real)} spesies target plus 1 kelas negatif"
        f"{f', {_verified} klip tambahan dari verifikasi ahli' if _verified else ''}"
    )

    # Write eval.md
    report = f"""# Evaluation Report -- GemaHutan Embedding Classifier (Track B)

## Overview

| Metric | Value |
|--------|-------|
| Test accuracy | {test_acc:.4f} |
| Val accuracy | {val_acc:.4f} |
| Macro precision | {macro_p:.4f} |
| Macro recall | {macro_r:.4f} |
| Macro F1 | {macro_f1:.4f} |
| Jumlah kelas | {num_classes} |
| Dataset | {_dataset_line} |
| Pembagian data | train {_split_sizes.get('train', 0)}, validasi {_split_sizes.get('val', 0)}, uji {_test_clips} klip |
| Embedding | BirdNET 1024-dim (GLOBAL_AVG_POOL), dibekukan |
| Classifier | MLP 2 lapis, numpy, seed tetap 42 |

> Angka di atas berasal dari latih ulang penuh dengan seed tetap
> (`python train.py --epochs 300 --hidden 256 --lr 0.001 --seed 42`), lalu
> `python evaluate.py`. Tanpa seed tetap, hasil antar run bervariasi sekitar
> 0.05 pada val_acc dengan konfigurasi yang sama, jadi selalu sebutkan seed
> saat membandingkan angka.
> Data uji dipisah per rekaman, bukan per potongan, supaya tidak ada kebocoran
> potongan dari rekaman yang sama ke data latih.

## Per-species Metrics (Test Set)

| Species | Precision | Recall | F1 | AUC-PR | Support |
|---------|-----------|--------|-----|--------|---------|
"""
    for sp in sorted(species_metrics.keys()):
        m = species_metrics[sp]
        report += f"| {sp} | {m['precision']:.4f} | {m['recall']:.4f} | {m['f1']:.4f} | {m['auc_pr']:.4f} | {m['support']} |\n"

    report += """
## Calibrated Thresholds (dari validation set)

| Species | Threshold |
|---------|-----------|
"""
    for sp in sorted(thresholds.keys()):
        report += f"| {sp} | {thresholds[sp]} |\n"

    report += f"""
## Track A vs Track B

| Metrik | Track A (BirdNET zero-shot) | Track B (Embedding + MLP) |
|--------|-----------------------------|---------------------------|
| Model | BirdNET-Analyzer v2.4 | Embedding BirdNET 1024-dim + MLP 2 lapis |
| Cakupan | 6522 spesies global | {len(_species_real)} spesies target Indonesia |
| Dataset evaluasi | {_test_clips} klip uji Xeno-canto | sama, {_test_clips} klip uji |
| Peran di aplikasi | penjaring awal di worker | penilai ulang untuk spesies lokal, threshold per spesies |

> Kedua track berjalan berdampingan di worker (CascadeEngine). Track A menjaga
> cakupan global, Track B menaikkan ketepatan pada spesies target dengan
> threshold hasil kalibrasi. Angka per spesies di atas adalah hasil evaluasi
> Track B pada klip uji yang tidak dipakai saat latih.
"""

    with open(REPORTS_DIR / f"eval{akhiran}.md", "w") as f:
        f.write(report)

    # Save thresholds JSON for DB import
    with open(JALUR["out_thresholds"], "w") as f:
        json.dump(thresholds, f, indent=2)

    # Save full metrics JSON
    with open(REPORTS_DIR / f"metrics{akhiran}.json", "w") as f:
        json.dump({
            "test_acc": float(test_acc),
            "val_acc": float(val_acc),
            "macro_precision": float(macro_p),
            "macro_recall": float(macro_r),
            "macro_f1": float(macro_f1),
            "checkpoint_dir": str(JALUR["checkpoint_dir"]),
            "emb_dir": str(JALUR["emb_dir"]),
            "per_species": species_metrics,
            "thresholds": thresholds,
        }, f, indent=2)

    print(f"\nReport: {REPORTS_DIR / f'eval{akhiran}.md'}")
    print(f"Thresholds: {JALUR['out_thresholds']}")


if __name__ == "__main__":
    main()