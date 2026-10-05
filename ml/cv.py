"""5-fold stratified cross-validation untuk MLP classifier.

Mengambil seluruh klip ND-free (train+val+test digabung), buat stratified
k-fold via sklearn, latih ulang konfigurasi produksi untuk setiap fold,
laporkan mean +/- std test_acc, F1 makro, dan tabel per-spesies mean +/- std.

Output:
  - ml/reports/cv_report.json   (angka lengkap)
  - ml/reports/cv_report.md     (ringkasan manusiawi)
  - ml/reports/cv_per_fold.json (per-fold metrics untuk plot)
"""
import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
from sklearn.model_selection import StratifiedKFold

ML_DIR = Path(__file__).resolve().parent
REPO_DIR = ML_DIR.parent
sys.path.insert(0, str(ML_DIR))

import train as train_mod  # noqa: E402

EMB_DIR = train_mod.EMB_DIR
CHECKPOINT_DIR = train_mod.CHECKPOINT_DIR
SPLITS_FILE = train_mod.SPLITS_FILE
REPORTS_DIR = train_mod.REPORTS_DIR


def load_all_data():
    """Gabungkan train+val+test jadi satu set."""
    embeddings = np.load(EMB_DIR / "embeddings.npy")
    labels = np.load(EMB_DIR / "labels.npy")
    with open(EMB_DIR / "clip_ids.json") as f:
        clip_ids = json.load(f)
    with open(EMB_DIR / "label_map.json") as f:
        label_map = json.load(f)
    with open(SPLITS_FILE) as f:
        splits = json.load(f)
    cid_to_idx = {cid: i for i, cid in enumerate(clip_ids)}

    all_ids = list(splits["train"]) + list(splits["val"]) + list(splits["test"])
    all_ids = [cid for cid in all_ids if cid in cid_to_idx]
    idx = [cid_to_idx[cid] for cid in all_ids]
    X = embeddings[idx]
    y = labels[idx]
    return X, y, all_ids, label_map


def run_cv(n_splits: int = 5, epochs: int = 200, hidden: int = 256,
           lr: float = 0.001, batch_size: int = 64, seed: int = 42):
    """Latih n_splits fold stratified, kembalikan dict ringkasan."""
    X, y, all_ids, label_map = load_all_data()
    n_classes = len(label_map)
    print(f"CV pool: {len(X)} samples, {n_classes} classes, n_splits={n_splits}")

    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=seed)
    fold_metrics = []
    per_class_acc = {sp: [] for sp in label_map.keys()}

    args = argparse.Namespace(
        seed=seed, epochs=epochs, hidden=hidden, lr=lr,
        batch_size=batch_size, resume=False, limit=None, seed_list="",
    )

    for fold_idx, (tr_idx, te_idx) in enumerate(skf.split(X, y)):
        t0 = time.time()
        X_train, y_train = X[tr_idx], y[tr_idx]
        X_test, y_test = X[te_idx], y[te_idx]
        # Validasi = 10% stratified dari train fold untuk early stop & LR.
        rng = np.random.default_rng(seed + fold_idx)
        val_n = max(1, int(round(0.1 * len(X_train))))
        val_sel = rng.choice(len(X_train), size=val_n, replace=False)
        val_mask = np.zeros(len(X_train), dtype=bool)
        val_mask[val_sel] = True
        X_val = X_train[val_mask]
        y_val = y_train[val_mask]
        keep_mask = ~val_mask
        X_train_f = X_train[keep_mask]
        y_train_f = y_train[keep_mask]

        # Normalisasi fit di training fold only, terapkan ke val/test.
        mean = X_train_f.mean(axis=0)
        std = X_train_f.std(axis=0) + 1e-8
        X_train_f = (X_train_f - mean) / std
        X_val = (X_val - mean) / std
        X_test = (X_test - mean) / std

        print(f"\n=== Fold {fold_idx + 1}/{n_splits} "
              f"train={len(X_train_f)} val={len(X_val)} test={len(X_test)} ===")
        result = train_mod.train_one(
            X_train_f, y_train_f, X_val, y_val, X_test, y_test,
            n_classes, X_train_f.shape[1], args, CHECKPOINT_DIR,
        )
        test_preds = result["model"].predict(X_test)
        # Akurasi per spesies di fold ini.
        for c, sp in enumerate(sorted(label_map.keys(), key=lambda k: label_map[k])):
            mask = y_test == c
            if mask.sum() == 0:
                continue
            per_class_acc[sp].append(float(np.mean(test_preds[mask] == c)))
        fold_metrics.append({
            "fold": fold_idx + 1,
            "train_size": int(len(X_train_f)),
            "val_size": int(len(X_val)),
            "test_size": int(len(X_test)),
            "best_val_acc": result["best_val_acc"],
            "test_acc": result["test_acc"],
            "f1_macro": result["f1_macro"],
            "epochs_trained": len(result["history"]),
            "temperature": result["temperature"],
            "elapsed_s": round(time.time() - t0, 1),
        })
        print(f"  fold {fold_idx + 1}: best_val_acc={result['best_val_acc']:.4f} "
              f"test_acc={result['test_acc']:.4f} f1={result['f1_macro']:.4f}")

    val_arr = np.array([m["best_val_acc"] for m in fold_metrics])
    test_arr = np.array([m["test_acc"] for m in fold_metrics])
    f1_arr = np.array([m["f1_macro"] for m in fold_metrics])

    per_class_summary = {}
    for sp, accs in per_class_acc.items():
        if not accs:
            continue
        arr = np.array(accs)
        per_class_summary[sp] = {
            "mean": float(arr.mean()),
            "std": float(arr.std(ddof=1)) if len(accs) > 1 else 0.0,
            "n_folds_with_class_in_test": len(accs),
            "per_fold": [float(a) for a in accs],
        }

    summary = {
        "n_splits": n_splits,
        "n_total_samples": int(len(X)),
        "n_classes": n_classes,
        "config": {
            "epochs": epochs, "hidden": hidden, "lr": lr,
            "batch_size": batch_size, "seed": seed,
            "dropout": 0.3, "weight_decay": 1e-4,
            "early_stop_patience": 30,
            "lr_schedule": "ReduceLROnPlateau(factor=0.5,patience=15,min=1e-5)",
            "class_weight": "balanced via sklearn",
        },
        "best_val_acc_mean": float(val_arr.mean()),
        "best_val_acc_std": float(val_arr.std(ddof=1)) if n_splits > 1 else 0.0,
        "test_acc_mean": float(test_arr.mean()),
        "test_acc_std": float(test_arr.std(ddof=1)) if n_splits > 1 else 0.0,
        "f1_macro_mean": float(f1_arr.mean()),
        "f1_macro_std": float(f1_arr.std(ddof=1)) if n_splits > 1 else 0.0,
        "per_fold": fold_metrics,
        "per_class_accuracy": per_class_summary,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    return summary


def write_markdown(summary, out_path):
    """Tulis ringkasan manusiawi ke .md."""
    lines = []
    lines.append(f"# Cross-Validation Report ({summary['n_splits']}-fold stratified)")
    lines.append("")
    lines.append(f"- Pool: {summary['n_total_samples']} samples, {summary['n_classes']} classes")
    cfg = summary["config"]
    lines.append(f"- Config: epochs={cfg['epochs']} hidden={cfg['hidden']} lr={cfg['lr']} "
                 f"dropout={cfg['dropout']} wd={cfg['weight_decay']} seed={cfg['seed']}")
    lines.append(f"- LR schedule: {cfg['lr_schedule']}")
    lines.append(f"- Class weight: {cfg['class_weight']}")
    lines.append("")
    lines.append("## Headline metrics (mean +/- std)")
    lines.append("")
    lines.append(f"- Best val acc: {summary['best_val_acc_mean']:.4f} +/- {summary['best_val_acc_std']:.4f}")
    lines.append(f"- Test acc:    {summary['test_acc_mean']:.4f} +/- {summary['test_acc_std']:.4f}")
    lines.append(f"- F1 macro:    {summary['f1_macro_mean']:.4f} +/- {summary['f1_macro_std']:.4f}")
    lines.append("")
    lines.append("## Per-fold")
    lines.append("")
    lines.append("| Fold | Train | Val | Test | best_val_acc | test_acc | F1 macro | Epochs |")
    lines.append("|---:|---:|---:|---:|---:|---:|---:|---:|")
    for m in summary["per_fold"]:
        lines.append(f"| {m['fold']} | {m['train_size']} | {m['val_size']} | {m['test_size']} "
                     f"| {m['best_val_acc']:.4f} | {m['test_acc']:.4f} | {m['f1_macro']:.4f} "
                     f"| {m['epochs_trained']} |")
    lines.append("")
    lines.append("## Per-class accuracy (mean +/- std across folds)")
    lines.append("")
    lines.append("| Species | mean | std | folds_with_class |")
    lines.append("|---|---:|---:|---:|")
    for sp, v in sorted(summary["per_class_accuracy"].items(),
                        key=lambda kv: -kv[1]["mean"]):
        lines.append(f"| {sp} | {v['mean']:.4f} | {v['std']:.4f} | {v['n_folds_with_class_in_test']} |")
    out_path.write_text("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n-splits", type=int, default=5)
    parser.add_argument("--epochs", type=int, default=200,
                        help="Epoch per fold (lebih kecil dari produksi 300 untuk durasi CV).")
    parser.add_argument("--seed", type=int, default=42)
    args_cli = parser.parse_args()

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    summary = run_cv(n_splits=args_cli.n_splits, epochs=args_cli.epochs,
                     seed=args_cli.seed)

    (REPORTS_DIR / "cv_report.json").write_text(json.dumps(summary, indent=2))
    write_markdown(summary, REPORTS_DIR / "cv_report.md")
    (REPORTS_DIR / "cv_per_fold.json").write_text(
        json.dumps({"per_fold": summary["per_fold"],
                    "headline": {
                        "test_acc_mean": summary["test_acc_mean"],
                        "test_acc_std": summary["test_acc_std"],
                        "f1_macro_mean": summary["f1_macro_mean"],
                        "f1_macro_std": summary["f1_macro_std"],
                    }}, indent=2))
    print("\n=== CV headline ===")
    print(f"  test_acc = {summary['test_acc_mean']:.4f} +/- {summary['test_acc_std']:.4f}")
    print(f"  f1_macro = {summary['f1_macro_mean']:.4f} +/- {summary['f1_macro_std']:.4f}")
    print(f"Disimpan ke {REPORTS_DIR}/cv_report.json dan cv_report.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())