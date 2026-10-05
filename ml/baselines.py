"""Baseline comparison: 4 baseline pada subset 50 klip uji (stratified).

a) majority class (selalu predict _negative)
b) sklearn LogisticRegression pada BirdNET embedding
c) sklearn MLPClassifier (256 hidden) pada BirdNET embedding
d) model sekarang + threshold (best_model + thresholds)

Hasil:
  ml/reports/baselines.json
  ml/reports/baselines.md
"""
import json
import sys
from pathlib import Path

import numpy as np

ML_DIR = Path(__file__).resolve().parent
REPO_DIR = ML_DIR.parent
sys.path.insert(0, str(REPO_DIR))
sys.path.insert(0, str(ML_DIR))


EMB_DIR = ML_DIR / "embeddings"
CKPT = ML_DIR / "checkpoints" / "best_model.npz"
NORM = ML_DIR / "checkpoints" / "normalization.npz"
SPLITS = ML_DIR / "data" / "splits.json"
THR = ML_DIR / "reports" / "thresholds.json"
REPORTS = ML_DIR / "reports"


def muat_subset_uji(n_maks=50, seed=42):
    import random

    random.seed(seed)
    with open(EMB_DIR / "label_map.json") as f:
        label_map = json.load(f)
    emb = np.load(EMB_DIR / "embeddings.npy")
    labels = np.load(EMB_DIR / "labels.npy")
    with open(EMB_DIR / "clip_ids.json") as f:
        ids = json.load(f)
    with open(SPLITS) as f:
        sp = json.load(f)
    cid_idx = {c: i for i, c in enumerate(ids)}
    test_idx = [cid_idx[c] for c in sp["test"] if c in cid_idx]
    by_class = {}
    for i in test_idx:
        by_class.setdefault(int(labels[i]), []).append(i)
    pilih = []
    for _cls, lst in by_class.items():
        random.shuffle(lst)
        pilih.extend(lst[:3])
    random.shuffle(pilih)
    pilih = pilih[:n_maks]
    return emb[pilih], labels[pilih], label_map


def sklearn_metrics(preds, y, n_classes):
    acc = float(np.mean(preds == y))
    f1s = []
    for c in range(n_classes):
        tp = int(np.sum((preds == c) & (y == c)))
        fp = int(np.sum((preds == c) & (y != c)))
        fn = int(np.sum((preds != c) & (y == c)))
        if tp == 0:
            f1s.append(0.0)
            continue
        prec = tp / (tp + fp)
        rec = tp / (tp + fn)
        f1s.append(2 * prec * rec / (prec + rec))
    return acc, float(np.mean(f1s))


def main():
    from sklearn.linear_model import LogisticRegression
    from sklearn.neural_network import MLPClassifier

    X, y, label_map = muat_subset_uji(n_maks=50)
    n_classes = len(label_map)
    print(f"Subset uji: {len(y)} jendela, {n_classes} kelas")

    # Muat train subset untuk fitting sklearn.
    with open(SPLITS) as f:
        sp = json.load(f)
    with open(EMB_DIR / "clip_ids.json") as f:
        ids = json.load(f)
    emb_all = np.load(EMB_DIR / "embeddings.npy")
    labels_all = np.load(EMB_DIR / "labels.npy")
    cid_idx = {c: i for i, c in enumerate(ids)}
    train_idx = [cid_idx[c] for c in sp["train"] if c in cid_idx]
    X_train = emb_all[train_idx]
    y_train = labels_all[train_idx]

    norm = np.load(NORM)
    mean, std = norm["mean"], norm["std"]
    X_train_norm = (X_train - mean) / std
    X_test_norm = (X - mean) / std

    # a) majority class.
    kelas_negatif = label_map["_negative"]
    preds = np.full(len(y), kelas_negatif, dtype=int)
    acc, f1 = sklearn_metrics(preds, y, n_classes)
    hasil = {"a_mayoritas_selalu_negative": {"test_acc": acc, "macro_f1": f1,
                                             "n": int(len(y)),
                                             "note": "predict selalu _negative"}}

    # b) LogisticRegression pada BirdNET embedding.
    print("  fit LogisticRegression ...")
    lr = LogisticRegression(max_iter=400, n_jobs=-1, random_state=42)
    lr.fit(X_train_norm, y_train)
    preds = lr.predict(X_test_norm)
    acc, f1 = sklearn_metrics(preds, y, n_classes)
    hasil["b_logreg_birdnet"] = {
        "test_acc": acc, "macro_f1": f1, "n": int(len(y))}

    # c) sklearn MLPClassifier (256 hidden) pada BirdNET embedding.
    print("  fit MLPClassifier sklearn ...")
    mlp = MLPClassifier(hidden_layer_sizes=(256,), max_iter=80,
                        learning_rate_init=0.001, random_state=42,
                        early_stopping=False)
    mlp.fit(X_train_norm, y_train)
    preds = mlp.predict(X_test_norm)
    acc, f1 = sklearn_metrics(preds, y, n_classes)
    hasil["c_sklearn_mlp_birdnet"] = {
        "test_acc": acc, "macro_f1": f1, "n": int(len(y))}

    # d) Model produksi + threshold.
    from ml.model_loader import dengan_kalibrasi, muat
    model, mean, std = muat()
    raw = model.forward(X_test_norm)
    probs = dengan_kalibrasi(raw)
    thresholds = json.loads(THR.read_text())
    preds = np.zeros(len(X), dtype=int)
    for i in range(len(X)):
        diizinkan = [c for c, nama in enumerate(label_map)
                     if probs[i, c] >= thresholds.get(nama, 0.0)]
        if not diizinkan:
            diizinkan = [int(np.argmax(probs[i]))]
        preds[i] = diizinkan[np.argmax(probs[i, diizinkan])]
    acc, f1 = sklearn_metrics(preds, y, n_classes)
    hasil["d_model_threshold"] = {
        "test_acc": acc, "macro_f1": f1, "n": int(len(y))}

    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "baselines.json").write_text(json.dumps(hasil, indent=2))

    md = ["# Baseline Comparison (subset 50/127 jendela uji, stratified)",
          "",
          "Subset sama untuk semua baseline (stratified max 3 per kelas).",
          "",
          "| # | Baseline | test_acc | macro_F1 | Catatan |",
          "|---|----------|----------|----------|---------|"]
    label_desk = {
        "a_mayoritas_selalu_negative": "a) Mayoritas (predict selalu _negative)",
        "b_logreg_birdnet": "b) sklearn LogisticRegression + BirdNET",
        "c_sklearn_mlp_birdnet": "c) sklearn MLPClassifier (256) + BirdNET",
        "d_model_threshold": "d) Model produksi (numpy MLP) + threshold per spesies",
    }
    for k, v in hasil.items():
        cat = v.get("note", "-")
        md.append(f"| {label_desk[k].split(')')[0]} | "
                  f"{label_desk[k].split(') ',1)[1]} | "
                  f"{v['test_acc']:.4f} | {v['macro_f1']:.4f} | {cat} |")
    md.append("")
    md.append("## Catatan")
    md.append("")
    md.append("- Mayoritas (a) sengaja rendah karena selalu tebak _negative.")
    md.append("- LogReg (b) dan MLP sklearn (c) memakai embedding yang sama, "
              "jadi selisih mencerminkan kapasitas pemodelan.")
    md.append("- Model (d) produksi sengaja dibandingkan head-to-head dengan sklearn "
              "(c) untuk menunjukkan bahwa implementasi numpy kami tidak kalah.")
    md.append("- Subset 50 klip (bukan 127) demi kecepatan. Angka tidak boleh "
              "dibandingkan langsung dengan angka uji penuh 127.")
    md.append("")
    md.append("> Angka pembanding eksternal (mis. eBird, Merlin) TIDAK disertakan "
              "karena tidak ada otorisasi untuk mengklaim itu di proposal. "
              "Pembanding hanya pada baselines internal di atas.")
    (REPORTS / "baselines.md").write_text("\n".join(md))
    print(f"  tulis {REPORTS / 'baselines.md'}")
    print(f"  tulis {REPORTS / 'baselines.json'}")


if __name__ == "__main__":
    main()