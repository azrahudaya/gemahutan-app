"""Calibrate confidence with vector scaling.

Temperature + per-class additive bias. Equivalent to Platt scaling for
multi-class: logits_calibrated = (logits + bias) / T.

T+T_vector biasanya bisa menurunkan NLL >5% ketika model underconfident
pada kelas tertentu (mis. _negative dominan di val).
"""

import json
import sys
from pathlib import Path

import numpy as np

ML_DIR = Path(__file__).parent
CHECKPOINT_DIR = ML_DIR / "checkpoints"
EMB_DIR = ML_DIR / "embeddings"
SPLITS_FILE = ML_DIR / "data" / "splits.json"


def load_data(split_name):
    embeddings = np.load(EMB_DIR / "embeddings.npy")
    labels = np.load(EMB_DIR / "labels.npy")
    clip_ids = json.load(open(EMB_DIR / "clip_ids.json"))
    splits = json.load(open(SPLITS_FILE))
    cid_to_idx = {cid: i for i, cid in enumerate(clip_ids)}
    X, y = [], []
    for cid in splits[split_name]:
        if cid in cid_to_idx:
            X.append(embeddings[cid_to_idx[cid]])
            y.append(labels[cid_to_idx[cid]])
    return np.array(X), np.array(y)


def load_model():
    sys.path.insert(0, str(ML_DIR))
    from train import MLP
    norm = np.load(CHECKPOINT_DIR / "normalization.npz")
    label_map = json.load(open(EMB_DIR / "label_map.json"))
    model = MLP(1024, 256, len(label_map), lr=0.001)
    model.load(str(CHECKPOINT_DIR / "best_model.npz"))
    return model, norm, label_map


def forward_logits(model, X):
    z1 = X @ model.W1 + model.b1
    a1 = np.maximum(0, z1)
    z2 = a1 @ model.W2 + model.b2
    return z2


def softmax(z):
    z = z - np.max(z, axis=-1, keepdims=True)
    ez = np.exp(z)
    return ez / np.sum(ez, axis=-1, keepdims=True)


def nll(logits, y, T, b):
    p = softmax((logits + b) / T)
    p_y = p[np.arange(len(y)), y]
    return float(-np.mean(np.log(p_y + 1e-12)))


def fit_vector_scaling(logits, y, n_classes, lr=0.05, steps=400, l2=0.5):
    """Joint optimization of T and bias vector dengan L2 regularisasi pada bias.

    l2 mencegah bias drift liar yang menurunkan NLL train tapi gagal di val.
    """
    T = 1.0
    b = np.zeros(n_classes, dtype=np.float32)
    n = len(y)
    best_state = (T.copy() if isinstance(T, np.ndarray) else T, b.copy(), float("inf"))
    prev = float("inf")
    for _step in range(steps):
        scaled = (logits + b) / T
        scaled = scaled - scaled.max(axis=-1, keepdims=True)
        ez = np.exp(scaled)
        p = ez / ez.sum(axis=-1, keepdims=True)
        loss = -np.mean(np.log(p[np.arange(n), y] + 1e-12)) + l2 * (b ** 2).mean()

        # gradient
        onehot = np.zeros_like(p)
        onehot[np.arange(n), y] = 1.0
        d_scaled = (p - onehot) / n  # (n, C)

        # db : d(loss)/db = sum_i (1/T) d_scaled_i
        db = (d_scaled.sum(axis=0)) / T + 2 * l2 * b / n_classes

        # dT: chain rule
        # loss = -mean log p_y, p = softmax(z/T)
        # dlog p_y / dT = -1/T * (1 - p_y) + sum_c p_c * (-z_c/T^2)
        # cukup: d_loss/dT = (1/n) sum_i (z_logit_minus_avg)/T^2 for y class

        # Simplify: d_loss/dT estimated numerically
        eps = 1e-3
        loss_p = nll(logits, y, T + eps, b)
        loss_m = nll(logits, y, T - eps, b)
        dT = (loss_p - loss_m) / (2 * eps)

        # Update
        T = max(0.05, T - lr * dT)
        b = b - lr * db

        if loss < best_state[2]:
            best_state = (T, b.copy(), loss)
        if abs(prev - loss) < 1e-7:
            break
        prev = loss
    return best_state[0], best_state[1], best_state[2]


def main():
    X, y = load_data("val")
    print(f"Val samples: {len(X)}")
    model, norm, label_map = load_model()
    X_n = (X - norm["mean"]) / norm["std"]
    logits = forward_logits(model, X_n)
    n_classes = len(label_map)
    print(f"Logits shape: {logits.shape}, classes: {n_classes}")

    nll_before = nll(logits, y, 1.0, np.zeros(n_classes))
    print(f"Val NLL sebelum (T=1, b=0): {nll_before:.6f}")

    # Joint optimization T + bias
    best = (1.0, np.zeros(n_classes), nll_before)
    for lr in (0.05, 0.02, 0.005):
        for l2 in (0.0, 0.1, 0.5, 2.0):
            T_c, b_c, nll_c = fit_vector_scaling(logits, y, n_classes, lr=lr, steps=500, l2=l2)
            if nll_c < best[2]:
                best = (T_c, b_c, nll_c)

    T_used, b_used, nll_after = best
    improvement = (nll_before - nll_after) / nll_before * 100.0
    print(f"T={T_used:.4f}, |b|max={np.abs(b_used).max():.4f}")
    print(f"Val NLL sesudah: {nll_after:.6f}")
    print(f"NLL turun: {improvement:.2f}% (target >=5%)")

    # Sanity: kelas tertinggi harus identik (terutama utk top-1)
    p_orig = softmax(logits)
    p_cal = softmax((logits + b_used) / T_used)
    top_orig = np.argmax(p_orig, axis=1)
    top_cal = np.argmax(p_cal, axis=1)
    n_changed = int(np.sum(top_orig != top_cal))
    print(f"Perubahan prediksi top-1: {n_changed} dari {len(X)}")

    # ECE quick check
    ece_before = ece(p_orig, top_orig, y)
    ece_after = ece(p_cal, top_cal, y)
    print(f"ECE sebelum: {ece_before:.4f}")
    print(f"ECE sesudah: {ece_after:.4f}")

    # Persist
    out = {
        "method": "vector_scaling_T+b",
        "temperature": float(T_used),
        "bias": b_used.tolist(),
        "nll_before": float(nll_before),
        "nll_after": float(nll_after),
        "nll_improvement_pct": round(float(improvement), 4),
        "ece_before": float(ece_before),
        "ece_after": float(ece_after),
        "top1_predictions_changed": n_changed,
        "val_samples": int(len(X)),
        "num_classes": int(n_classes),
        "label_map": label_map,
    }
    target = CHECKPOINT_DIR / "temperature.json"
    target.write_text(json.dumps(out, indent=2))
    print(f"Disimpan ke {target}")

    if improvement < 5.0:
        print(f"GAGAL: NLL hanya turun {improvement:.2f}% (<5%).")
        return 1
    return 0


def ece(probs, preds, y, n_bins=10):
    """Expected Calibration Error, binning by confidence."""
    confs = probs.max(axis=1)
    accs = (preds == y).astype(float)
    ece_v = 0.0
    for i in range(n_bins):
        lo, hi = i / n_bins, (i + 1) / n_bins
        mask = (confs >= lo) & (confs < hi)
        if mask.any():
            gap = abs(confs[mask].mean() - accs[mask].mean())
            ece_v += (mask.sum() / len(confs)) * gap
    return float(ece_v)


if __name__ == "__main__":
    sys.exit(main())
