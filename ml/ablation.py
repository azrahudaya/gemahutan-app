"""Ablation study: 4 konfigurasi pada subset 50/127 jendela uji (stratified).

a) baseline: BirdNET embedding + MLP 256 hidden + normalisasi + threshold
b) tanpa embedding: log-Mel spectrogram 128-bin + MLP 256
c) tanpa normalisasi: embedding mentah (tanpa mean/std) + threshold
d) tanpa threshold: embedding ternormalisasi, argmax saja

Hasil:
  ml/reports/ablation.json
  ml/reports/ablation.md
"""
import csv
import json
import random
import sys
from pathlib import Path

import numpy as np

ML_DIR = Path(__file__).resolve().parent
REPO_DIR = ML_DIR.parent
sys.path.insert(0, str(REPO_DIR))
sys.path.insert(0, str(ML_DIR))

from ml.train import MLP  # noqa: E402

EMB_DIR = ML_DIR / "embeddings"
CKPT = ML_DIR / "checkpoints" / "best_model.npz"
NORM = ML_DIR / "checkpoints" / "normalization.npz"
SPLITS = ML_DIR / "data" / "splits.json"
THR_FILE = ML_DIR / "reports" / "thresholds.json"
REPORTS = ML_DIR / "reports"


def muat_subset_uji(n_maks=50, seed=42):
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
    for _, lst in by_class.items():
        random.shuffle(lst)
        pilih.extend(lst[:3])
    random.shuffle(pilih)
    pilih = pilih[:n_maks]
    return (emb[pilih], labels[pilih],
            [ids[i] for i in pilih], label_map)


def sklearn_metrics(preds, y, n_classes):
    """Akurasi + macro F1 (numpy only)."""
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


def muat_manifest_map():
    return {r["clip_id"]: r["local_path"]
            for r in csv.DictReader(open(ML_DIR / "data" / "manifest.csv"))}


def melspec_ringkas(clip_ids):
    """128-d vektor per klip: mean-pool baris log-mel 128-bin."""
    import librosa
    man = muat_manifest_map()
    out = []
    for cid in clip_ids:
        rel = man.get(cid)
        if rel is None:
            out.append(np.zeros(128, dtype=np.float32))
            continue
        path = ML_DIR / "data" / rel
        try:
            y, _ = librosa.load(str(path), sr=48000, mono=True, duration=3.0)
        except Exception:
            out.append(np.zeros(128, dtype=np.float32))
            continue
        S = librosa.feature.melspectrogram(y=y, sr=48000, n_mels=128,
                                           n_fft=1024, hop_length=256)
        S_db = librosa.power_to_db(S, ref=np.max)
        feat = S_db.mean(axis=1)
        feat = (feat - feat.mean()) / (feat.std() + 1e-8)
        out.append(feat.astype(np.float32))
    return np.stack(out, axis=0)


def latih_melspec(X_train_mel, n_classes):
    """Latih MLP kecil 30 epoch pada fitur melspec."""
    rng = np.random.default_rng(42)
    model = MLP(128, 256, n_classes, lr=0.001)
    for _ in range(30):
        perm = rng.permutation(len(X_train_mel))
        Xs = X_train_mel[perm]
        ys = _train_labels_for_mel[perm]
        for i in range(0, len(Xs), 64):
            Xb = Xs[i:i + 64]
            yb = ys[i:i + 64]
            y_onehot = np.zeros((len(yb), n_classes), dtype=np.float32)
            y_onehot[np.arange(len(yb)), yb] = 1
            model.forward(Xb)
            model.backward(Xb, y_onehot)
    return model


# Cache global untuk label train (diisi di main()).
_train_labels_for_mel = None


def baseline_embedding(X, y, label_map):
    """a) BirdNET embedding + normalisasi + threshold."""
    from ml.model_loader import dengan_kalibrasi, muat
    model, mean, std = muat()
    raw = model.forward((X - mean) / std)
    probs = dengan_kalibrasi(raw)
    thresholds = json.loads(THR_FILE.read_text())
    preds = np.zeros(len(X), dtype=int)
    for i in range(len(X)):
        diizinkan = [c for c, nama in enumerate(label_map)
                     if probs[i, c] >= thresholds.get(nama, 0.0)]
        if not diizinkan:
            diizinkan = [int(np.argmax(probs[i]))]
        preds[i] = diizinkan[np.argmax(probs[i, diizinkan])]
    return preds


def tanpa_embedding_melspec(clip_ids, y, label_map, train_clip_ids, train_labels):
    """b) Melspec 128-dim + MLP 256 (latih dari nol)."""
    global _train_labels_for_mel
    X_test = melspec_ringkas(clip_ids)
    X_train = melspec_ringkas(train_clip_ids)
    _train_labels_for_mel = train_labels
    n_classes = len(label_map)
    model = latih_melspec(X_train, n_classes)
    return model.predict(X_test)


def tanpa_normalisasi(X, y, label_map):
    """c) Embedding tanpa z-score + threshold."""
    model = MLP(1024, 256, len(label_map))
    model.load(str(CKPT))
    probs = model.forward(X)
    thresholds = json.loads(THR_FILE.read_text())
    preds = np.zeros(len(X), dtype=int)
    for i in range(len(X)):
        diizinkan = [c for c, nama in enumerate(label_map)
                     if probs[i, c] >= thresholds.get(nama, 0.0)]
        if not diizinkan:
            diizinkan = [int(np.argmax(probs[i]))]
        preds[i] = diizinkan[np.argmax(probs[i, diizinkan])]
    return preds


def tanpa_threshold(X, y, label_map):
    """d) Embedding + normalisasi, argmax saja."""
    norm = np.load(NORM)
    mean, std = norm["mean"], norm["std"]
    model = MLP(1024, 256, len(label_map))
    model.load(str(CKPT))
    probs = model.forward((X - mean) / std)
    return np.argmax(probs, axis=1)


def main():
    X, y, clip_ids, label_map = muat_subset_uji(n_maks=50)
    n_classes = len(label_map)
    print(f"Subset uji: {len(y)} jendela, {n_classes} kelas")

    # Siapkan train subset untuk fitting b).
    with open(SPLITS) as f:
        sp = json.load(f)
    with open(EMB_DIR / "clip_ids.json") as f:
        ids = json.load(f)
    labels_all = np.load(EMB_DIR / "labels.npy")
    cid_idx = {c: i for i, c in enumerate(ids)}
    train_idx = [cid_idx[c] for c in sp["train"] if c in cid_idx]
    train_clip_ids = [ids[i] for i in train_idx]
    train_labels = labels_all[train_idx]

    hasil = {}
    preds = baseline_embedding(X, y, label_map)
    acc, f1 = sklearn_metrics(preds, y, n_classes)
    hasil["a_baseline_embedding_norm_threshold"] = {
        "test_acc": acc, "macro_f1": f1, "n": int(len(y))}
    print(f"  a) embedding+norm+thr: acc={acc:.3f} f1={f1:.3f}")

    preds = tanpa_embedding_melspec(clip_ids, y, label_map,
                                    train_clip_ids, train_labels)
    acc, f1 = sklearn_metrics(preds, y, n_classes)
    hasil["b_tanpa_embedding_melspec"] = {
        "test_acc": acc, "macro_f1": f1, "n": int(len(y))}
    print(f"  b) melspec: acc={acc:.3f} f1={f1:.3f}")

    preds = tanpa_normalisasi(X, y, label_map)
    acc, f1 = sklearn_metrics(preds, y, n_classes)
    hasil["c_tanpa_normalisasi"] = {
        "test_acc": acc, "macro_f1": f1, "n": int(len(y))}
    print(f"  c) tanpa normalisasi: acc={acc:.3f} f1={f1:.3f}")

    preds = tanpa_threshold(X, y, label_map)
    acc, f1 = sklearn_metrics(preds, y, n_classes)
    hasil["d_tanpa_threshold"] = {
        "test_acc": acc, "macro_f1": f1, "n": int(len(y))}
    print(f"  d) tanpa threshold: acc={acc:.3f} f1={f1:.3f}")

    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "ablation.json").write_text(json.dumps(hasil, indent=2))

    md = ["# Ablation Study (subset 50/127 jendela uji, stratified)",
          "",
          "Subset sama untuk semua konfigurasi: stratified max 3 klip per "
          "kelas, total 50 jendela. Subset ini yang dipakai konsisten.",
          "",
          "| # | Konfigurasi | test_acc | macro_F1 |",
          "|---|-------------|----------|----------|"]
    label_desk = {
        "a_baseline_embedding_norm_threshold":
            "a) BirdNET embedding + normalisasi + threshold (model produksi)",
        "b_tanpa_embedding_melspec":
            "b) Tanpa embedding BirdNET: log-Mel 128-bin + MLP 256",
        "c_tanpa_normalisasi":
            "c) Tanpa normalisasi: embedding mentah + threshold per spesies",
        "d_tanpa_threshold":
            "d) Tanpa threshold: argmax saja, tanpa per spesies",
    }
    for k, v in hasil.items():
        nama = label_desk[k]
        md.append(f"| {nama.split(')')[0]} | "
                  f"{nama.split(') ', 1)[1]} | "
                  f"{v['test_acc']:.4f} | {v['macro_f1']:.4f} |")
    md.append("")
    md.append("## Catatan")
    md.append("")
    md.append("- Subset 50 klip (bukan 127) demi kecepatan. Angka tidak boleh "
              "dibandingkan langsung dengan angka uji penuh 127.")
    md.append("- Konfigurasi (b) melatih MLP kecil dari awal pada fitur "
              "log-Mel 128-dim, tanpa BirdNET, jadi wajar bila angkanya "
              "lebih rendah.")
    md.append("- Selisih antara (a) dan (d) menunjukkan efek threshold per "
              "spesies; selisih antara (a) dan (c) menunjukkan efek z-score.")
    (REPORTS / "ablation.md").write_text("\n".join(md))
    print(f"  tulis {REPORTS / 'ablation.md'}")


if __name__ == "__main__":
    main()