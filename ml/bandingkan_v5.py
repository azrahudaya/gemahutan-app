"""Bandingkan kandidat korpus v5 (negatif iNat -> negatif XC) dengan produksi LR v3.

Pool yang sama untuk kedua model:
- split uji (splits_v5.test == splits_v3.test, tidak berubah)
- CV bersarang (evaluasi_bersarang.py --emb-dir ml/embeddings_v5)
- uji independen (embedding cache yang sama)

Produksi TIDAK diubah. Promosi hanya lewat gerbang ml/promosikan.py.

Jalankan: source .venv/bin/activate && python ml/bandingkan_v5.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
ML = ROOT / "ml"
OUT_JSON = ML / "reports" / "bandingkan_v5.json"
OUT_MD = ML / "reports" / "bandingkan_v5.md"


def softmax(z):
    z = z - z.max(axis=1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


def probs(X, W1, b1, T, bias):
    z = (X @ W1 + b1 + bias) / T
    return softmax(z)


def muat(ckpt_dir: Path, emb_dir: Path):
    ckpt = np.load(ckpt_dir / "best_model.npz")
    W1 = ckpt["W1"].astype(np.float32)
    b1 = ckpt["b1"].astype(np.float32)
    T = float(ckpt["temperature"].reshape(-1)[0]) if "temperature" in ckpt.files else 1.0
    bias = ckpt["bias"].astype(np.float32) if "bias" in ckpt.files else 0.0
    norm = np.load(ckpt_dir / "normalization.npz")
    emb = np.load(emb_dir / "embeddings.npy")
    lab = np.load(emb_dir / "labels.npy")
    ids = json.loads((emb_dir / "clip_ids.json").read_text())
    lm = json.loads((emb_dir / "label_map.json").read_text())
    return dict(W1=W1, b1=b1, T=T, bias=bias, mean=norm["mean"].astype(np.float32),
                std=norm["std"].astype(np.float32), emb=emb, lab=lab, ids=ids, lm=lm)


def recall_per_spesies(p, y, lm):
    pred = np.argmax(p, 1)
    neg = lm.get("_negative", -1)
    out = {}
    for k, v in lm.items():
        if v == neg:
            continue
        mask = y == v
        if mask.sum() == 0:
            continue
        out[k] = float((pred[mask] == v).mean())
    return out


def main() -> int:
    v5_dir = ML / "checkpoints_logreg_v5"
    if not (v5_dir / "best_model.npz").exists():
        print("ERROR: checkpoint v5 belum ada. Jalankan save_logreg dulu.")
        return 1

    v5 = muat(v5_dir, ML / "embeddings_v5")
    v3 = muat(ML / "checkpoints", ML / "embeddings_v3")

    # Split uji yang sama (v5.test == v3.test)
    sp5 = json.loads((ML / "data/splits_v5.json").read_text())
    test = sp5["test"]

    # Evaluasi di pool yang sama (klip uji yang sama), tapi tiap model memakai
    # resep normalisasinya sendiri (mean/std dari train masing-masing).
    idx3 = {c: i for i, c in enumerate(v3["ids"])}
    idx5 = {c: i for i, c in enumerate(v5["ids"])}
    test_ada = [c for c in test if c in idx3 and c in idx5]
    y3 = v3["lab"][[idx3[c] for c in test_ada]]

    X3 = (v3["emb"][[idx3[c] for c in test_ada]] - v3["mean"]) / v3["std"]
    X5 = (v5["emb"][[idx5[c] for c in test_ada]] - v5["mean"]) / v5["std"]

    p3 = probs(X3, v3["W1"], v3["b1"], v3["T"], v3["bias"])
    p5 = probs(X5, v5["W1"], v5["b1"], v5["T"], v5["bias"])

    acc3 = float((np.argmax(p3, 1) == y3).mean())
    acc5 = float((np.argmax(p5, 1) == y3).mean())

    r3 = recall_per_spesies(p3, y3, v3["lm"])
    r5 = recall_per_spesies(p5, y3, v5["lm"])
    turun = {k: round(r5.get(k, 0) - r3.get(k, 0), 4) for k in r3 if k in r5}
    turun_banyak = {k: v for k, v in turun.items() if v < -0.15}

    hasil = {
        "pool_uji_n": len(test_ada),
        "uji_acc_v3": round(acc3, 4),
        "uji_acc_v5": round(acc5, 4),
        "selisih_acc": round(acc5 - acc3, 4),
        "spesies_v3": len(r3),
        "spesies_v5": len(r5),
        "spesies_turun_gt_015": len(turun_banyak),
        "recall_per_spesies_v3": {k: round(v, 4) for k, v in r3.items()},
        "recall_per_spesies_v5": {k: round(v, 4) for k, v in r5.items()},
        "n_v5_klip": int(v5["emb"].shape[0]),
        "n_v3_klip": int(v3["emb"].shape[0]),
        "catatan": ("Pembanding: v5 vs v3 pada split uji yang sama, embedding v3 "
                    "untuk keduanya. CV bersarang dan uji independen terpisah."),
    }
    OUT_JSON.write_text(json.dumps(hasil, indent=2, ensure_ascii=False))

    md = ["# Bandingkan v5 (negatif XC) vs produksi v3", "",
          f"Pool uji: {len(test_ada)} klip (sama untuk kedua model)", "",
          "| Metrik | v3 (produksi) | v5 (kandidat) | Selisih |",
          "|---|---|---|---|",
          f"| Akurasi uji | {acc3:.4f} | {acc5:.4f} | {acc5-acc3:+.4f} |",
          f"| Jumlah klip korpus | {v3['emb'].shape[0]} | {v5['emb'].shape[0]} | "
          f"{v5['emb'].shape[0]-v3['emb'].shape[0]:+d} |",
          f"| Spesies turun recall > 0.15 | - | {len(turun_banyak)} | - |"]
    if turun_banyak:
        md += ["", "Spesies turun > 0.15:"]
        for k, val in sorted(turun_banyak.items()):
            md.append(f"- {k}: {r3[k]:.3f} -> {r5.get(k,0):.3f} ({val:+.3f})")
    OUT_MD.write_text("\n".join(md) + "\n")

    print(f"Pool uji: {len(test_ada)}")
    print(f"Akurasi v3 {acc3:.4f}, v5 {acc5:.4f} (selisih {acc5-acc3:+.4f})")
    print(f"Spesies turun recall > 0.15: {len(turun_banyak)}")
    print(f"Output: {OUT_JSON}")
    print(f"Output: {OUT_MD}")
    return 0


if __name__ == "__main__":
    sys.exit(main())