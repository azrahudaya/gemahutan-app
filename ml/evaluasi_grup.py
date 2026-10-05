"""Evaluasi berkelompok (grouped CV) + uji independen.

StratifiedGroupKFold 5 lipatan atas semua klip berlabel XC (grup dari M03).
Korpus non-XC selalu di latih (tidak ikut CV). Keluaran:
- OOF probs, acc, macro F1, per spesies, bootstrap CI95, ECE
- Laporan uji independen dengan model penuh (latih di semua XC + non-XC)

Semua metrik berasal dari OOF, bukan dari test split 127 klip.
"""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.model_selection import StratifiedGroupKFold  # noqa: E402

ML_DIR = ROOT / "ml"
EMB_DIR = ML_DIR / "embeddings_v3"
SPLITS_FILE = ML_DIR / "data" / "splits_v3.json"
XC_META_FILE = ML_DIR / "data" / "xc_meta.json"
UJI_DIR = ML_DIR / "data" / "uji_independen"
OUT_JSON = ML_DIR / "reports" / "eval_grup.json"
OUT_MD = ML_DIR / "reports" / "eval_grup.md"

N_FOLDS = 5
C = 1.0
SEED = 2026


def softmax(z):
    z = z - z.max(axis=1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


def bootstrap_ci95(metric_fn, y_true, y_pred_probs, n_boot=2000):
    """Bootstrap 95% CI untuk metrik agregat."""
    rng = np.random.default_rng(SEED)
    vals = []
    n = len(y_true)
    for _ in range(n_boot):
        idx = rng.choice(n, size=n, replace=True)
        vals.append(metric_fn(y_true[idx], y_pred_probs[idx]))
    vals = np.array(vals)
    return float(np.mean(vals)), float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))


def accuracy_from_probs(probs, y_true):
    return float(np.mean(np.argmax(probs, axis=1) == y_true))


def macro_f1_from_probs(probs, y_true):
    preds = np.argmax(probs, axis=1)
    n_classes = probs.shape[1]
    f1s = []
    for c in range(n_classes):
        tp = np.sum((preds == c) & (y_true == c))
        fp = np.sum((preds == c) & (y_true != c))
        fn = np.sum((preds != c) & (y_true == c))
        if tp + fp == 0 or tp + fn == 0:
            f1s.append(0.0)
        else:
            prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1s.append(2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0)
    return float(np.mean(f1s))


def ece(probs, y_true, n_bins=10):
    """Expected Calibration Error."""
    confs = np.max(probs, axis=1)
    preds = np.argmax(probs, axis=1)
    correct = (preds == y_true).astype(np.float64)
    bins = np.linspace(0, 1, n_bins + 1)
    ece_sum = 0.0
    for i in range(n_bins):
        mask = (confs >= bins[i]) & (confs < bins[i + 1])
        if mask.sum() > 0:
            bin_acc = correct[mask].mean()
            bin_conf = confs[mask].mean()
            ece_sum += mask.sum() * abs(bin_acc - bin_conf)
    return float(ece_sum / len(y_true))


def per_species_f1(probs, y_true, label_map):
    """F1 per spesies dari softmax probabilities."""
    preds = np.argmax(probs, axis=1)
    inv = {v: k for k, v in label_map.items()}
    n_classes = probs.shape[1]
    result = {}
    for c in range(n_classes):
        tp = int(np.sum((preds == c) & (y_true == c)))
        fp = int(np.sum((preds == c) & (y_true != c)))
        fn = int(np.sum((preds != c) & (y_true == c)))
        support = int(np.sum(y_true == c))
        if tp + fp == 0 or tp + fn == 0:
            result[inv.get(c, str(c))] = {"f1": 0.0, "precision": 0.0, "recall": 0.0, "support": support}
        else:
            prec = tp / (tp + fp)
            rec = tp / (tp + fn)
            f1 = 2 * prec * rec / (prec + rec)
            result[inv.get(c, str(c))] = {"f1": round(f1, 4), "precision": round(prec, 4),
                                           "recall": round(rec, 4), "support": support}
    return result


def load_embeddings_and_labels():
    """Load embeddings, labels, splits, dan label map."""
    emb_all = np.load(EMB_DIR / "embeddings.npy")
    labels_all = np.load(EMB_DIR / "labels.npy")
    clip_ids = json.loads((EMB_DIR / "clip_ids.json").read_text())
    label_map = json.loads((EMB_DIR / "label_map.json").read_text())
    splits = json.loads(SPLITS_FILE.read_text())
    return emb_all, labels_all, clip_ids, label_map, splits


def get_groups(clip_ids):
    """Dapatkan grup dari xc_meta.json untuk semua clip_ids.

    xc_meta.json punya dua sumber:
    1. groups = {nama_perekam: [list_clip_ids]}  (format baru, dari E01)
    2. recordings = {clip_id: {rec: ..., ...}}   (format per-klip)

    Fungsi ini membaca kedua sumber, memprioritaskan recordings (lebih granular).
    """
    if not XC_META_FILE.exists():
        print(f"WARNING: {XC_META_FILE} not found, using clip_id as group")
        return {cid: cid for cid in clip_ids}

    meta = json.loads(XC_META_FILE.read_text())

    # Bangun lookup dari recordings (sumber utama, per-klip)
    recs = meta.get("recordings", {})
    result = {}
    for cid in clip_ids:
        if cid in recs and recs[cid].get("rec"):
            result[cid] = recs[cid]["rec"]
        elif cid.startswith("xc-"):
            # Fallback: rantai XC number
            try:
                num = int(cid.replace("xc-neg-", "").replace("xc-", ""))
                result[cid] = f"xc_chain_{num // 10}"
            except ValueError:
                result[cid] = cid
        else:
            result[cid] = cid
    return result


def main():
    print("Loading data...")
    emb_all, labels_all, clip_ids, label_map, splits = load_embeddings_and_labels()
    cid_to_idx = {cid: i for i, cid in enumerate(clip_ids)}
    norm = np.load(ML_DIR / "checkpoints" / "normalization.npz")
    mean, std = norm["mean"], norm["std"]

    # Identifikasi klip XC vs non-XC
    xc_ids = [cid for cid in clip_ids if cid.startswith("xc-")]
    non_xc_ids = [cid for cid in clip_ids if not cid.startswith("xc-")]
    print(f"XC clips: {len(xc_ids)}, non-XC: {len(non_xc_ids)}")

    groups_all = get_groups(clip_ids)

    # Ambil hanya XC clips yang ada di splits (train/val/test) — tapi
    # kita pakai SEMUA untuk CV, bukan hanya train split.
    xc_labels = np.array([labels_all[cid_to_idx[cid]] for cid in xc_ids])
    xc_groups = np.array([groups_all[cid] for cid in xc_ids])

    # Non-XC: selalu latih
    non_xc_idx = np.array([cid_to_idx[cid] for cid in non_xc_ids])
    non_xc_labels = labels_all[non_xc_idx]
    non_xc_emb = (emb_all[non_xc_idx] - mean) / std

    # CV pada XC clips saja
    sgkf = StratifiedGroupKFold(n_splits=N_FOLDS, shuffle=True, random_state=SEED)

    n_classes = len(label_map)
    oof_probs = np.zeros((len(xc_ids), n_classes), dtype=np.float32)
    fold_results = []

    for fold, (train_idx, val_idx) in enumerate(sgkf.split(xc_ids, xc_labels, groups=xc_groups)):
        print(f"\nFold {fold + 1}/{N_FOLDS}: {len(train_idx)} train, {len(val_idx)} val")

        # XC train + non-XC train
        xc_train_idx = np.array([cid_to_idx[cid] for cid in np.array(xc_ids)[train_idx]])
        xc_val_idx = np.array([cid_to_idx[cid] for cid in np.array(xc_ids)[val_idx]])

        X_train = np.vstack([
            (emb_all[xc_train_idx] - mean) / std,
            non_xc_emb,
        ]).astype(np.float32)
        y_train = np.concatenate([labels_all[xc_train_idx], non_xc_labels])

        X_val = ((emb_all[xc_val_idx] - mean) / std).astype(np.float32)
        y_val = labels_all[xc_val_idx]

        # Latih LogReg
        lr = LogisticRegression(max_iter=3000, C=C, class_weight="balanced")
        lr.fit(X_train, y_train)

        probs_val = lr.predict_proba(X_val)
        oof_probs[val_idx] = probs_val

        acc = accuracy_from_probs(probs_val, y_val)
        f1 = macro_f1_from_probs(probs_val, y_val)
        fold_results.append({"fold": fold, "n_train": len(X_train), "n_val": len(X_val),
                             "acc": round(acc, 4), "f1_macro": round(f1, 4)})
        print(f"  acc={acc:.4f}, f1_macro={f1:.4f}")

    # Agregat OOF
    acc = accuracy_from_probs(oof_probs, xc_labels)
    f1 = macro_f1_from_probs(oof_probs, xc_labels)
    ece_val = ece(oof_probs, xc_labels)

    acc_mean, acc_lo, acc_hi = bootstrap_ci95(lambda y, p: accuracy_from_probs(p, y),
                                               xc_labels, oof_probs)
    f1_mean, f1_lo, f1_hi = bootstrap_ci95(lambda y, p: macro_f1_from_probs(p, y),
                                            xc_labels, oof_probs)

    per_sp = per_species_f1(oof_probs, xc_labels, label_map)

    output = {
        "method": "StratifiedGroupKFold",
        "n_folds": N_FOLDS,
        "n_xc_clips": len(xc_ids),
        "n_non_xc_clips": len(non_xc_ids),
        "n_classes": n_classes,
        "C": C,
        "seed": SEED,
        "aggregate": {
            "accuracy": round(acc, 4),
            "accuracy_ci95": [round(acc_lo, 4), round(acc_hi, 4)],
            "macro_f1": round(f1, 4),
            "macro_f1_ci95": [round(f1_lo, 4), round(f1_hi, 4)],
            "ece": round(ece_val, 4),
        },
        "per_fold": fold_results,
        "per_species": per_sp,
    }

    # Simpan OOF probs + labels untuk M06 (kalibrasi dari OOF)
    oof_dir = ML_DIR / "reports" / "oof"
    oof_dir.mkdir(parents=True, exist_ok=True)
    np.savez(oof_dir / "oof_probs.npz", probs=oof_probs, labels=xc_labels)
    with open(oof_dir / "oof_xc_ids.json", "w") as f:
        json.dump(xc_ids, f)
    print(f"OOF probs saved to {oof_dir}")

    # Evaluasi uji independen dengan model penuh.
    print("\n--- Evaluasi uji independen ---")
    uji_emb_path = UJI_DIR / "embeddings.npy"
    if not uji_emb_path.exists():
        print("  embeddings.npy not found, skipping independent test")
        print("  (run ml/uji_independen.py to compute embeddings from audio)")
    else:
        import csv
        uji_manifest = UJI_DIR / "manifest.csv"
        uji_emb_all = np.load(uji_emb_path)
        uji_ids = json.loads((UJI_DIR / "clip_ids.json").read_text())
        uji_labels = np.load(UJI_DIR / "labels.npy")
        uji_norm = np.load(UJI_DIR / "normalization.npz")

        # Latih model penuh di SEMUA XC + non-XC
        all_xc_idx = np.array([cid_to_idx[cid] for cid in xc_ids])
        X_full = np.vstack([
            (emb_all[all_xc_idx] - mean) / std,
            non_xc_emb,
        ]).astype(np.float32)
        y_full = np.concatenate([labels_all[all_xc_idx], non_xc_labels])

        lr_full = LogisticRegression(max_iter=3000, C=C, class_weight="balanced")
        lr_full.fit(X_full, y_full)

        # Ambil subset yang ada di manifest
        manifest_ids = set()
        with open(uji_manifest, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                cid = row.get("clip_id", "").strip()
                if cid:
                    manifest_ids.add(cid)

        uji_idx = [i for i, cid in enumerate(uji_ids) if cid in manifest_ids]
        if uji_idx:
            X_uji = ((uji_emb_all[uji_idx] - uji_norm["mean"]) / uji_norm["std"]).astype(np.float32)
            y_uji = uji_labels[uji_idx]
            probs_uji = lr_full.predict_proba(X_uji)
            acc_uji = accuracy_from_probs(probs_uji, y_uji)
            f1_uji = macro_f1_from_probs(probs_uji, y_uji)
            ece_uji = ece(probs_uji, y_uji)
            acc_u_mean, acc_u_lo, acc_u_hi = bootstrap_ci95(
                lambda y, p: accuracy_from_probs(p, y), y_uji, probs_uji)
            f1_u_mean, f1_u_lo, f1_u_hi = bootstrap_ci95(
                lambda y, p: macro_f1_from_probs(p, y), y_uji, probs_uji)

            output["independent_test"] = {
                "n_clips": len(uji_idx),
                "accuracy": round(acc_uji, 4),
                "accuracy_ci95": [round(acc_u_lo, 4), round(acc_u_hi, 4)],
                "macro_f1": round(f1_uji, 4),
                "macro_f1_ci95": [round(f1_u_lo, 4), round(f1_u_hi, 4)],
                "ece": round(ece_uji, 4),
            }
            per_sp_uji = per_species_f1(probs_uji, y_uji, label_map)
            output["independent_test"]["per_species"] = per_sp_uji

    # Simpan JSON
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(output, indent=2, ensure_ascii=False))
    print(f"\nSaved to {OUT_JSON}")

    # Render markdown
    lines = [
        "# Evaluasi Berkelompok (Grouped CV)",
        "",
        f"- Metode: StratifiedGroupKFold {N_FOLDS}-fold",
        f"- Klip XC: {len(xc_ids)}",
        f"- Klip non-XC (selalu latih): {len(non_xc_ids)}",
        f"- C: {C}, class_weight: balanced",
        f"- Seed: {SEED}",
        "",
        "## Agregat OOF",
        "",
        "| Metrik | Nilai | CI95 |",
        "|--------|-------|------|",
        f"| Accuracy | {acc:.4f} | [{acc_lo:.3f}, {acc_hi:.3f}] |",
        f"| Macro F1 | {f1:.4f} | [{f1_lo:.3f}, {f1_hi:.3f}] |",
        f"| ECE | {ece_val:.4f} | - |",
        "",
        "## Per Fold",
        "",
    ]
    for fr in fold_results:
        lines.append(f"- Fold {fr['fold'] + 1}: n_train={fr['n_train']}, n_val={fr['n_val']}, "
                     f"acc={fr['acc']:.4f}, f1={fr['f1_macro']:.4f}")

    lines += [
        "",
        "## Per Spesies (OOF)",
        "",
        "| Spesies | Support | F1 | Precision | Recall |",
        "|---------|---------|----|-----------|--------|",
    ]
    for sp, vals in sorted(per_sp.items()):
        lines.append(f"| {sp} | {vals['support']} | {vals['f1']:.4f} | {vals['precision']:.4f} | {vals['recall']:.4f} |")

    if "independent_test" in output:
        it = output["independent_test"]
        lines += [
            "",
            "## Uji Independen",
            "",
            f"- Klip: {it['n_clips']} (negara lain)",
            f"- Accuracy: {it['accuracy']:.4f} [{it['accuracy_ci95'][0]:.3f}, {it['accuracy_ci95'][1]:.3f}]",
            f"- Macro F1: {it['macro_f1']:.4f} [{it['macro_f1_ci95'][0]:.3f}, {it['macro_f1_ci95'][1]:.3f}]",
            f"- ECE: {it['ece']:.4f}",
        ]

    OUT_MD.write_text("\n".join(lines) + "\n")
    print(f"Saved to {OUT_MD}")
    return 0


if __name__ == "__main__":
    sys.exit(main())