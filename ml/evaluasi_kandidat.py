"""Evaluasi model v4_logreg pada split uji dan tulis gerbang.json.

Membandingkan model v4 (lisensi bersih + jendela terbaik) dengan LR v3 pada
angka yang sama: akurasi uji, dan recall per spesies OOF.

Jalankan: .venv/bin/python ml/evaluasi_kandidat.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
ML = ROOT / "ml"


def softmax(z):
    z = z - z.max(axis=1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


def muat_model(ckpt_dir: str, emb_dir: str):
    ckpt = np.load(ML / ckpt_dir / "best_model.npz")
    W1 = ckpt["W1"].astype(np.float32)
    b1 = ckpt["b1"].astype(np.float32)
    T = float(ckpt["temperature"].reshape(-1)[0]) if "temperature" in ckpt.files else 1.0
    bias = ckpt["bias"].astype(np.float32) if "bias" in ckpt.files else 0.0
    norm = np.load(ML / ckpt_dir / "normalization.npz")
    mean = norm["mean"].astype(np.float32)
    std = norm["std"].astype(np.float32)
    emb = np.load(ML / emb_dir / "embeddings.npy")
    lab = np.load(ML / emb_dir / "labels.npy")
    ids = json.loads((ML / emb_dir / "clip_ids.json").read_text())
    label_map = json.loads((ML / emb_dir / "label_map.json").read_text())
    return W1, b1, T, bias, mean, std, emb, lab, ids, label_map


def probs(X, W1, b1, T, bias):
    z = (X @ W1 + b1 + bias) / T
    return softmax(z)


def main() -> int:
    # Model v4 (kandidat) memakai embedding v4_terpilih + norm v4_terpilih.
    W1v4, b1v4, Tv4, biasv4, mean4, std4, emb4, lab4, ids4, lm4 = muat_model(
        "runs/v4_logreg", "embeddings_v4_terpilih")
    # Model v3 (produksi) memakai embedding v3 + norm v3 (dari checkpoints).
    W1v3, b1v3, Tv3, biasv3, mean3, std3, emb3, lab3, ids3, lm3 = muat_model(
        "checkpoints", "embeddings_v3")

    sp = json.loads((ML / "data/splits_v4.json").read_text())
    test = sp["test"]

    # Uji memakai embedding v3 (single-window) untuk kedua model, supaya adil.
    idx3 = {c: i for i, c in enumerate(ids3)}
    test_ada = [c for c in test if c in idx3]
    X3 = (emb3[[idx3[c] for c in test_ada]] - mean3) / std3
    y3 = lab3[[idx3[c] for c in test_ada]]

    p_v3 = probs(X3, W1v3, b1v3, Tv3, biasv3)
    p_v4 = probs(X3, W1v4, b1v4, Tv4, biasv4)

    acc3 = float((np.argmax(p_v3, 1) == y3).mean())
    acc4 = float((np.argmax(p_v4, 1) == y3).mean())
    print(f"uji (n={len(test_ada)}): LR v3 acc {acc3:.4f}, v4 acc {acc4:.4f}")

    # Recall per spesies (top-1, tanpa ambang).
    def recall_per_spesies(p, y, lm):
        pred = np.argmax(p, 1)
        out = {}
        for k, v in lm.items():
            if v == lm.get("_negative", -1):
                continue
            mask = y == v
            if mask.sum() == 0:
                continue
            out[k] = float((pred[mask] == v).mean())
        return out

    r3 = recall_per_spesies(p_v3, y3, lm3)
    r4 = recall_per_spesies(p_v4, y3, lm3)
    turun = {k: (r4.get(k, 0) - r3.get(k, 0)) for k in r3 if k in r4}
    turun_banyak = {k: v for k, v in turun.items() if v < -0.15}
    print(f"spesies turun recall > 0.15: {len(turun_banyak)}")
    for k, v in sorted(turun.items()):
        if v < -0.10:
            print(f"  {k}: {r3[k]:.2f} -> {r4.get(k, 0):.2f} ({v:+.2f})")

    # Tulis gerbang.json (tanpa independen/e2e di sini; diisi manual di M02).
    gerbang = {
        "lulus": None,
        "uji_acc_v3": round(acc3, 4),
        "uji_acc_v4": round(acc4, 4),
        "selisih_acc": round(acc4 - acc3, 4),
        "spesies_turun_gt_015": len(turun_banyak),
        "catatan": "Uji memakai embedding v3 single-window untuk kedua model (adil). "
                   "Independen dan e2e belum dihitung di sini.",
    }
    out = ML / "runs/v4_logreg/gerbang.json"
    out.write_text(json.dumps(gerbang, indent=2, ensure_ascii=False))
    print(f"\ngerbang.json: {json.dumps(gerbang, indent=2, ensure_ascii=False)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
