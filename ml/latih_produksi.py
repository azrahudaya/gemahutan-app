"""Latih model produksi secara reproduksibel dari konfigurasi YAML.

Satu perintah: python ml/latih_produksi.py [--config ml/configs/lr_v3.yaml]

Output:
  ml/checkpoints/best_model.npz  (selalu identik untuk konfigurasi sama)
  ml/checkpoints/normalization.npz
  ml/checkpoints/label_map.json
  ml/checkpoints/meta.json       (git SHA, versi library, sha256 input)
  ml/reports/thresholds.json

Dua kali jalan dengan konfigurasi dan data sama = sha256 checkpoint identik.
"""
import argparse
import hashlib
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import sklearn  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402

from ml.train import MLP  # noqa: E402


def softmax(z):
    z = z - z.max(axis=1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


def nll(probs, y):
    return float(np.mean(-np.log(probs[np.arange(len(y)), y] + 1e-9)))


def sha256_file(path):
    """SHA-256 hash of a file."""
    if not path.exists():
        return None
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def sha256_bytes(data):
    """SHA-256 hash of bytes."""
    return hashlib.sha256(data).hexdigest()


def get_git_sha():
    """Dapatkan git SHA dari HEAD."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, cwd=str(ROOT), timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return "unknown"


def latih_temperature(logits, y):
    """Temperature scaling via grid search."""
    terbaik, nll_terbaik = 1.0, float("inf")
    for T in np.arange(0.05, 5.0, 0.005):
        nilai = nll(softmax(logits / T), y)
        if nilai < nll_terbaik:
            terbaik, nll_terbaik = float(T), nilai
    return terbaik, nll_terbaik


def latih_bias(logits, y, T, langkah=2000, lr=0.05):
    """Bias aditif per kelas."""
    n_kelas = logits.shape[1]
    bias = np.zeros(n_kelas, dtype=np.float32)
    satu_panas = np.zeros((len(y), n_kelas), dtype=np.float32)
    satu_panas[np.arange(len(y)), y] = 1.0
    for _ in range(langkah):
        probs = softmax((logits + bias) / T)
        grad = ((probs - satu_panas).mean(axis=0)).astype(np.float32)
        bias -= lr * grad
    return bias


def main():
    parser = argparse.ArgumentParser(description="Latih model produksi dari YAML config")
    parser.add_argument("--config", default=str(ROOT / "ml/configs/lr_v3.yaml"))
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"ERROR: config {config_path} not found")
        return 1

    cfg = yaml.safe_load(config_path.read_text())
    c = cfg["training"]
    d = cfg["data"]
    o = cfg["output"]

    emb_dir = ROOT / d["emb_dir"]
    splits_file = ROOT / d["splits_file"]
    ckpt_in = ROOT / d["ckpt_in"]
    ckpt_out = ROOT / o["ckpt_dir"]
    report_dir = ROOT / o["report_dir"]
    C = c["C"]
    seed = c["seed"]
    maks_negatif = c["maks_negatif"]

    # 1. Load data
    emb = np.load(emb_dir / "embeddings.npy")
    lab = np.load(emb_dir / "labels.npy")
    ids = json.loads((emb_dir / "clip_ids.json").read_text())
    label_map = json.loads((emb_dir / "label_map.json").read_text())
    sp = json.loads(splits_file.read_text())
    idx = {cid: i for i, cid in enumerate(ids)}

    rng = np.random.default_rng(seed)
    tr = [c for c in sp["train"] if c in idx]
    tr_lab = np.array([lab[idx[c]] for c in tr])

    # 2. Batasi negatif
    neg = label_map["_negative"]
    pos_neg = [i for i, c in enumerate(tr) if tr_lab[i] == neg]
    if len(pos_neg) > maks_negatif:
        buang = set(rng.choice(pos_neg, size=len(pos_neg) - maks_negatif, replace=False).tolist())
        tr = [c for i, c in enumerate(tr) if i not in buang]
        tr_lab = np.array([label for i, label in enumerate(tr_lab) if i not in buang])

    # 3. Normalisasi
    norm = np.load(ckpt_in / "normalization.npz")
    mean, std = norm["mean"], norm["std"]
    Xtr = ((emb[[idx[c] for c in tr]] - mean) / std).astype(np.float32)

    print(f"Latih LogReg pada {Xtr.shape[0]} klip (negatif <= {maks_negatif})")
    lr = LogisticRegression(max_iter=3000, C=C, class_weight="balanced")
    lr.fit(Xtr, tr_lab)

    # 4. Susun checkpoint format MLP linear
    n_kelas = len(label_map)
    model = MLP(Xtr.shape[1], n_kelas, n_kelas, dropout=0.0, activation="linear")
    model.W1 = np.ascontiguousarray(lr.coef_.T).astype(np.float32)
    model.b1 = np.ascontiguousarray(lr.intercept_).astype(np.float32)
    model.W2 = np.eye(n_kelas, dtype=np.float32)
    model.b2 = np.zeros(n_kelas, dtype=np.float32)
    model.training = False

    # 5. Kalibrasi di val
    val = [c for c in sp["val"] if c in idx]
    Xval = ((emb[[idx[c] for c in val]] - mean) / std).astype(np.float32)
    yval = lab[[idx[c] for c in val]]

    logits_val = Xval @ model.W1 + model.b1
    T, nll_T = latih_temperature(logits_val, yval)
    nll_awal = nll(softmax(logits_val), yval)
    bias = latih_bias(logits_val, yval, T)
    nll_akhir = nll(softmax((logits_val + bias) / T), yval)
    print(f"kalibrasi: T={T:.4f}  NLL {nll_awal:.4f} -> {nll_akhir:.4f}")

    # 6. Verifikasi reproduksi sklearn
    probs_model = softmax(Xval @ model.W1 + model.b1)
    probs_sklearn = lr.predict_proba(Xval)
    selisih = float(np.max(np.abs(probs_model - probs_sklearn)))
    print(f"selisih forward vs sklearn: {selisih:.8f}")
    assert selisih < 1e-4, f"tidak reproduksibel: {selisih}"

    # 7. Simpan checkpoint
    ckpt_out.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)

    model.save(str(ckpt_out / "best_model.npz"), temperature=T, bias=bias)
    np.savez(ckpt_out / "normalization.npz", mean=mean, std=std)
    json.dump(label_map, (ckpt_out / "label_map.json").open("w"), indent=2)

    # 8. Ambang per spesies
    probs_val = softmax((logits_val + bias) / T)
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
    json.dump(ambang, (report_dir / "thresholds.json").open("w"), indent=2)

    # 9. Meta.json: git SHA, versi, sha256 input
    # Hitung sha256 checkpoint setelah simpan
    ckpt_sha256 = sha256_file(ckpt_out / "best_model.npz")

    meta = {
        "config": str(config_path),
        "model_type": "logistic_regression_multikelas",
        "activation": "linear",
        "C": C,
        "class_weight": "balanced",
        "maks_negatif": maks_negatif,
        "seed": seed,
        "n_train": int(Xtr.shape[0]),
        "n_classes": n_kelas,
        "temperature": T,
        "nll_before": nll_awal,
        "nll_after": nll_akhir,
        "best_val_acc": float(np.mean(np.argmax(probs_val, axis=1) == yval)),
        "git_sha": get_git_sha(),
        "numpy_version": np.__version__,
        "sklearn_version": sklearn.__version__,
        "python_version": sys.version.split()[0],
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "sha256_embeddings": sha256_file(emb_dir / "embeddings.npy"),
        "sha256_splits": sha256_file(splits_file),
        "sha256_checkpoint": ckpt_sha256,
        "emb_dir": str(emb_dir),
        "splits_file": str(splits_file),
    }
    json.dump(meta, (ckpt_out / "meta.json").open("w"), indent=2)

    print(f"\ncheckpoint : {ckpt_out / 'best_model.npz'}")
    print(f"sha256     : {ckpt_sha256}")
    print(f"meta       : {ckpt_out / 'meta.json'}")
    print(f"ambang     : {report_dir / 'thresholds.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())