"""Tulis normalization.npz untuk embedding versi baru (prasyarat latih kandidat).

Jebakan yang dihindari: `ml/latih_produksi.py` MEMBACA `normalization.npz` dari
`data.ckpt_in`, bukan menghitungnya. Kalau config kandidat menunjuk
`ckpt_in: ml/checkpoints` sementara embeddingnya versi lain, maka mean/std
produksi dipakai pada distribusi yang berbeda, z-score jadi salah, dan SELURUH
angka evaluasi kandidat itu palsu.

Untuk K2 memakai ckpt_in produksi masih benar, karena embeddingnya sama persis
(`ml/embeddings_v3`) dan yang berubah hanya daftar klip latih. Untuk K3
embeddingnya BERBEDA (rata-rata jendela bersuara), jadi normalisasinya wajib
dihitung ulang dari klip LATIH versi itu.

mean/std dihitung HANYA dari klip latih+val menurut splits, jangan dari seluruh
berkas embedding, supaya statistik himpunan uji tidak bocor ke normalisasi.

Jalankan:
  source .venv/bin/activate && python ml/siapkan_norm_kandidat.py \
      --emb-dir ml/embeddings_bersuara_v3_klip \
      --splits ml/data/splits_v3_nd_bersih.json \
      --out-dir ml/runs/k3_ckpt_in
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
ML = ROOT / "ml"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--emb-dir", required=True)
    ap.add_argument("--splits", required=True)
    ap.add_argument("--out-dir", required=True)
    a = ap.parse_args()

    emb_dir = Path(a.emb_dir)
    out = Path(a.out_dir)
    emb = np.load(emb_dir / "embeddings.npy")
    ids = json.loads((emb_dir / "clip_ids.json").read_text())
    sp = json.loads(Path(a.splits).read_text())
    idx = {c: i for i, c in enumerate(ids)}

    latih = [c for c in (list(sp["train"]) + list(sp["val"])) if c in idx]
    if not latih:
        print("ERROR: tidak ada klip latih yang cocok dengan embedding")
        return 1
    X = emb[[idx[c] for c in latih]].astype(np.float32)

    mean = X.mean(axis=0)
    std = X.std(axis=0)
    # std nol membuat pembagian meledak; dijaga seperti resep produksi.
    std = np.where(std < 1e-6, 1.0, std).astype(np.float32)

    out.mkdir(parents=True, exist_ok=True)
    np.savez(out / "normalization.npz", mean=mean.astype(np.float32), std=std)
    (out / "label_map.json").write_text(
        (emb_dir / "label_map.json").read_text())

    print(f"klip latih dipakai: {len(latih)}")
    print(f"mean: {mean.shape}, std: {std.shape}, std minimum {float(std.min()):.6f}")
    print(f"Output: {out / 'normalization.npz'}")
    print("Pakai direktori ini sebagai `data.ckpt_in` di config kandidat.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
