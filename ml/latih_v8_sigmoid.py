"""Latih kandidat v8: kepala sigmoid (one-vs-rest) menggantikan softmax.

Satu perubahan terhadap v3: setiap spesies punya regresi logistik sendiri
(binary, sigmoid), bukan satu model softmax. Kelas _negative tetap sebagai
data negatif untuk setiap kepala.

Output di ml/runs/l7/v8/:
  best_model.npz, normalization.npz, label_map.json, meta.json, thresholds.json

Jalankan:
  python ml/latih_v8_sigmoid.py
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import sklearn  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.multiclass import OneVsRestClassifier  # noqa: E402

from ml.train import MLP  # noqa: E402


def sigmoid(z):
    return 1.0 / (1.0 + np.exp(-np.clip(z, -500, 500)))


def sha256_file(path):
    if not Path(path).exists():
        return None
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def get_git_sha():
    try:
        r = subprocess.run(["git", "rev-parse", "HEAD"],
                           capture_output=True, text=True, cwd=str(ROOT), timeout=5)
        if r.returncode == 0:
            return r.stdout.strip()
    except Exception:
        pass
    return "unknown"


def main():
    ML = ROOT / "ml"
    EMB_DIR = ML / "embeddings_v3"
    SPLITS = ML / "data" / "splits_v3.json"
    CKPT_IN = ML / "checkpoints"
    OUT = ML / "runs" / "l7" / "v8"

    C = 1.0
    SEED = 2024
    MAKS_NEG = 3000

    OUT.mkdir(parents=True, exist_ok=True)

    # 1. Load data
    emb = np.load(EMB_DIR / "embeddings.npy")
    lab = np.load(EMB_DIR / "labels.npy")
    ids = json.loads((EMB_DIR / "clip_ids.json").read_text())
    label_map = json.loads((EMB_DIR / "label_map.json").read_text())
    sp = json.loads(SPLITS.read_text())
    idx = {cid: i for i, cid in enumerate(ids)}

    rng = np.random.default_rng(SEED)
    tr = [c for c in sp["train"] if c in idx]
    tr_lab = np.array([lab[idx[c]] for c in tr])

    # 2. Batasi negatif
    neg_class = label_map["_negative"]
    pos_neg = [i for i, c in enumerate(tr) if tr_lab[i] == neg_class]
    if len(pos_neg) > MAKS_NEG:
        buang = set(rng.choice(pos_neg, size=len(pos_neg) - MAKS_NEG, replace=False).tolist())
        tr = [c for i, c in enumerate(tr) if i not in buang]
        tr_lab = np.array([label for i, label in enumerate(tr_lab) if i not in buang])

    # 3. Normalisasi
    norm = np.load(CKPT_IN / "normalization.npz")
    mean, std = norm["mean"], norm["std"]
    Xtr = ((emb[np.array([idx[c] for c in tr])] - mean) / std).astype(np.float32)

    # 4. One-vs-rest training
    n_kelas = len(label_map)
    print(f"Latih OVR sigmoid pada {Xtr.shape[0]} klip, {n_kelas} kelas")

    # Binarize labels: setiap kelas vs rest (termasuk _negative)
    from sklearn.preprocessing import label_binarize
    Y_bin = label_binarize(tr_lab, classes=list(range(n_kelas)))

    ovr = OneVsRestClassifier(
        LogisticRegression(C=C, max_iter=3000, class_weight="balanced", solver="lbfgs"),
        n_jobs=-1,
    )
    ovr.fit(Xtr, Y_bin)
    print("Training done")

    # 5. Buat checkpoint format MLP linear
    # OVR: setiap estimator punya coef_ (1, 1024) dan intercept_ (1,)
    # Stack jadi (1024, n_kelas) dan (n_kelas,)
    W = np.zeros((Xtr.shape[1], n_kelas), dtype=np.float32)
    b = np.zeros(n_kelas, dtype=np.float32)
    for i, est in enumerate(ovr.estimators_):
        W[:, i] = est.coef_.ravel()
        b[i] = est.intercept_.ravel()[0]

    model = MLP(Xtr.shape[1], n_kelas, n_kelas, dropout=0.0, activation="linear")
    model.W1 = np.ascontiguousarray(W).astype(np.float32)
    model.b1 = np.ascontiguousarray(b).astype(np.float32)
    model.W2 = np.eye(n_kelas, dtype=np.float32)
    model.b2 = np.zeros(n_kelas, dtype=np.float32)
    model.training = False

    # 6. Val set
    val = [c for c in sp["val"] if c in idx]
    Xval = ((emb[np.array([idx[c] for c in val])] - mean) / std).astype(np.float32)
    yval = lab[np.array([idx[c] for c in val])]

    logits_val = Xval @ W + b
    probs_val = sigmoid(logits_val)

    # Simpan tanpa temperature (sigmoid sudah terkalibrasi per kelas)
    # Temperature dan bias tidak relevan untuk OVR
    T = 1.0
    bias = np.zeros(n_kelas, dtype=np.float32)

    model.save(str(OUT / "best_model.npz"), temperature=T, bias=bias)
    np.savez(OUT / "normalization.npz", mean=mean, std=std)
    json.dump(label_map, (OUT / "label_map.json").open("w"), indent=2)

    # 7. Ambang per spesies (sigmoid-based)
    ambang = {}
    for nama, kelas in label_map.items():
        skor = probs_val[:, kelas]
        positif = yval == kelas
        if positif.sum() == 0:
            ambang[nama] = 0.5
            continue
        kandidat = np.unique(np.concatenate([skor, [0.0, 1.0]]))
        terbaik, f1_terbaik = 0.5, -1.0
        for t in kandidat:
            pred = skor >= t
            if pred.sum() == 0:
                continue
            tp = np.sum(pred & positif)
            fp = np.sum(pred & ~positif)
            fn = np.sum(~pred & positif)
            f1 = 2 * tp / (2 * tp + fp + fn) if (2 * tp + fp + fn) else 0.0
            if f1 > f1_terbaik:
                terbaik, f1_terbaik = float(t), f1
        ambang[nama] = terbaik
    json.dump(ambang, (OUT / "thresholds.json").open("w"), indent=2)

    # 8. Akurasi val (argmax, sama cara dengan v3)
    preds = np.argmax(probs_val, axis=1)
    val_acc = float(np.mean(preds == yval))
    print(f"Val acc (argmax): {val_acc:.4f}")

    # 9. Meta
    ckpt_sha = sha256_file(OUT / "best_model.npz")
    meta = {
        "config": "ml/configs/lr_v8_sigmoid.yaml",
        "model_type": "logistic_regression_ovr_sigmoid",
        "activation": "linear",
        "multi_class": "ovr",
        "C": C,
        "class_weight": "balanced",
        "maks_negatif": MAKS_NEG,
        "seed": SEED,
        "n_train": int(Xtr.shape[0]),
        "n_classes": n_kelas,
        "temperature": T,
        "best_val_acc": val_acc,
        "git_sha": get_git_sha(),
        "numpy_version": np.__version__,
        "sklearn_version": sklearn.__version__,
        "python_version": sys.version.split()[0],
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "sha256_embeddings": sha256_file(EMB_DIR / "embeddings.npy"),
        "sha256_splits": sha256_file(SPLITS),
        "sha256_checkpoint": ckpt_sha,
        "emb_dir": str(EMB_DIR),
        "splits_file": str(SPLITS),
        "perubahan": "softmax -> sigmoid (OVR), satu kepala per spesies",
    }
    json.dump(meta, (OUT / "meta.json").open("w"), indent=2)

    print(f"\ncheckpoint : {OUT / 'best_model.npz'}")
    print(f"sha256     : {ckpt_sha}")
    print(f"thresholds : {OUT / 'thresholds.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
