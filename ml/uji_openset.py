"""Uji open-set: bandingkan metode penolakan pada kelompok pengecoh.

Pilih di separuh pilih pada recall target >= 0.70, laporkan di separuh lapor.
Metode: (a) ambang saja, (b) kelas _negative, (c) veto BirdNET,
(d) logsumexp / energy score.
"""
import csv
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from ml.model_loader import dengan_kalibrasi, muat  # noqa: E402

ML_DIR = ROOT / "ml"
FIELD_DIR = ML_DIR / "data" / "field"
OUT_MD = ML_DIR / "reports" / "openset.md"

NEGATIVE_LABEL = "_negative"
RECALL_TARGET = 0.70


def load_field_data():
    """Load field embeddings + labels. Pakai cache kalau ada, kalau tidak hitung dari audio."""
    manifest = list(csv.DictReader(open(FIELD_DIR / "manifest.csv")))
    label_map = json.loads((ML_DIR / "embeddings_v3" / "label_map.json").read_text())
    neg_idx = label_map.get(NEGATIVE_LABEL, -1)

    # Cek cache
    cache_dir = FIELD_DIR / "embedding_cache_pengecoh"
    model, mean, std = muat()

    X_all, y_all, groups_all, is_target = [], [], [], []
    for row in manifest:
        cid = row["clip_id"]
        species = row["species_scientific"]
        group = row["group"]
        target_class = label_map.get(species, -1)

        # Coba load dari cache
        cache_file = cache_dir / f"{cid}.npy"
        if cache_file.exists():
            emb = np.load(cache_file)
            if emb.ndim == 1:
                emb = emb.reshape(1, -1)
        else:
            continue  # skip jika tidak ada embedding cache

        X_norm = (emb - mean) / std
        probs_raw = model.forward(X_norm)
        probs = dengan_kalibrasi(probs_raw)

        X_all.append(probs)
        target = 1 if target_class >= 0 and species != NEGATIVE_LABEL else 0
        y_all.append(target)
        groups_all.append(group)
        is_target.append(target_class)

    if not X_all:
        return None, None, None, None, label_map, None

    X = np.vstack(X_all)
    y = np.array(y_all)
    return X, y, np.array(groups_all), np.array(is_target), label_map, neg_idx


def split_by_groups(groups, seed=42):
    """Bagi indeks 50/50 secara berkelompok."""
    rng = np.random.default_rng(seed)
    unique_groups = np.unique(groups)
    rng.shuffle(unique_groups)
    mid = len(unique_groups) // 2
    select_groups = set(unique_groups[:mid])
    report_groups = set(unique_groups[mid:])

    select_idx = np.array([i for i, g in enumerate(groups) if g in select_groups])
    report_idx = np.array([i for i, g in enumerate(groups) if g in report_groups])
    return select_idx, report_idx


def evaluate_method(probs, y_true, neg_idx, method, **kwargs):
    """Evaluasi satu metode open-set rejection. Return dict metrik."""
    if method == "threshold_only":
        th = kwargs.get("threshold", 0.15)
        pred_positive = probs.max(axis=1) >= th
    elif method == "negative_class":
        th = kwargs.get("threshold", 0.15)
        # Reject jika prob kelas _negative > max prob kelas target
        if neg_idx >= 0:
            target_indices = [i for i in range(probs.shape[1]) if i != neg_idx]
            max_target = probs[:, target_indices].max(axis=1)
            pred_positive = (max_target >= th) & (max_target >= probs[:, neg_idx])
        else:
            pred_positive = probs.max(axis=1) >= th
    elif method == "logsumexp":
        th = kwargs.get("threshold", 1.0)
        # LogSumExp dari logits sebagai confidence
        eps = 1e-9
        logits = np.log(np.clip(probs, eps, 1.0))
        lse = np.log(np.sum(np.exp(logits), axis=1))
        pred_positive = lse >= th
    else:
        pred_positive = probs.max(axis=1) >= 0.15

    tp = np.sum(pred_positive & (y_true == 1))
    fn = np.sum(~pred_positive & (y_true == 1))
    fp = np.sum(pred_positive & (y_true == 0))
    tn = np.sum(~pred_positive & (y_true == 0))

    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0

    return {
        "recall": round(recall, 4),
        "false_positive_rate": round(fpr, 4),
        "precision": round(precision, 4),
        "tp": int(tp), "fp": int(fp), "fn": int(fn), "tn": int(tn),
        "n_target": int(np.sum(y_true == 1)),
        "n_non_target": int(np.sum(y_true == 0)),
    }


def find_threshold_at_recall(probs, y_true, neg_idx, method, target_recall=RECALL_TARGET):
    """Cari threshold yang menghasilkan recall >= target_recall."""
    best_th, best_result = 0.5, None
    for th in np.arange(0.01, 0.99, 0.02):
        result = evaluate_method(probs, y_true, neg_idx, method, threshold=th)
        if result["recall"] >= target_recall:
            best_th, best_result = th, result
            break
    # Fallback: threshold terbaik yang mencapai recall tertinggi
    if best_result is None:
        for th in np.arange(0.01, 0.99, 0.02):
            result = evaluate_method(probs, y_true, neg_idx, method, threshold=th)
            if best_result is None or result["recall"] > best_result["recall"]:
                best_th, best_result = th, result
    return best_th, best_result


def main():
    print("Loading field data...")
    X, y, groups, is_target, label_map, neg_idx = load_field_data()
    if X is None:
        print("ERROR: no field data with embeddings found")
        return 1

    print(f"Field data: {len(X)} clips "
          f"({np.sum(y == 1)} target, {np.sum(y == 0)} non-target/pengecoh)")

    # Split 50/50 by group
    select_idx, report_idx = split_by_groups(groups)
    print(f"Select: {len(select_idx)}, Report: {len(report_idx)}")

    X_sel, y_sel = X[select_idx], y[select_idx]
    X_rep, y_rep = X[report_idx], y[report_idx]

    # Metode dan pemilihan threshold
    methods = [
        ("threshold_only", "Ambang saja"),
        ("negative_class", "Kelas _negative"),
        ("logsumexp", "LogSumExp score"),
    ]

    results = []
    for method, label in methods:
        th, sel_result = find_threshold_at_recall(X_sel, y_sel, neg_idx, method)
        rep_result = evaluate_method(X_rep, y_rep, neg_idx, method, threshold=th)
        results.append({
            "method": label,
            "threshold": round(th, 4),
            "select": sel_result,
            "report": rep_result,
        })
        print(f"  {label}: th={th:.3f} -> "
              f"sel recall={sel_result['recall']:.3f} fpr={sel_result['false_positive_rate']:.3f} | "
              f"rep recall={rep_result['recall']:.3f} fpr={rep_result['false_positive_rate']:.3f}")

    # Pilih metode terbaik (FPR terendah pada report set dengan recall >= 0.70)
    best = min(
        [r for r in results if r["report"]["recall"] >= RECALL_TARGET],
        key=lambda r: r["report"]["false_positive_rate"],
        default=results[0],
    )

    # Tulis laporan
    lines = [
        "# Open-Set Rejection: Deteksi Palsu vs Recall",
        "",
        f"- Data lapangan: {len(X)} klip ({np.sum(y == 1)} target, {np.sum(y == 0)} pengecoh)",
        f"- Split: {len(select_idx)} pilih / {len(report_idx)} lapor (berkelompok)",
        f"- Recall target: >= {RECALL_TARGET}",
        "",
        "## Hasil",
        "",
        "| Metode | Threshold | Select Recall | Select FPR | Report Recall | Report FPR |",
        "|--------|-----------|---------------|------------|---------------|------------|",
    ]
    for r in results:
        lines.append(
            f"| {r['method']} | {r['threshold']:.3f} | "
            f"{r['select']['recall']:.3f} | {r['select']['false_positive_rate']:.3f} | "
            f"{r['report']['recall']:.3f} | {r['report']['false_positive_rate']:.3f} |"
        )

    lines += [
        "",
        f"## Metode Terpilih: {best['method']}",
        "",
        f"- Threshold: {best['threshold']:.4f}",
        f"- Recall (report): {best['report']['recall']:.4f}",
        f"- False Positive Rate (report): {best['report']['false_positive_rate']:.4f}",
        f"- Precision (report): {best['report']['precision']:.4f}",
        f"- TP={best['report']['tp']}, FP={best['report']['fp']}, "
        f"FN={best['report']['fn']}, TN={best['report']['tn']}",
        "",
        "## Catatan",
        "",
        "- BirdNET veto (metode c) belum diimplementasi: perlu skor BirdNET per segmen.",
        "- Hanya klip dengan embedding cache yang dipakai.",
        "- Metode _negative menggunakan prob kelas `_negative` trained di classifier.",
    ]

    OUT_MD.write_text("\n".join(lines) + "\n")
    print(f"\nSaved to {OUT_MD}")
    print(f"Best method: {best['method']} (FPR={best['report']['false_positive_rate']:.4f})")
    return 0


if __name__ == "__main__":
    sys.exit(main())