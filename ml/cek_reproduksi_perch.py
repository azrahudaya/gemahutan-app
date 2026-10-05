"""Periksa apakah ml/embeddings_perch/ (24 Sep) bisa direproduksi dengan bobot resmi.

Kenapa perlu: embedding Perch sesi lama tidak punya meta/params, dan folder bobot
`ml/models_perch/` tidak ada di mesin ini sampai sekarang. Sebelum angka K6
dipakai lebih jauh, 1536-dim lama harus dibuktikan berasal dari bobot yang sama.
Kalau cocok, embedding latih lama boleh dipakai; kalau tidak, harus ekstrak ulang.

Metode: ambil N klip acak (seed tetap) yang ada di clip_ids.json lama, hitung
ulang embedding-nya, bandingkan dengan cosine similarity dan selisih maksimum.

Jalankan: .venv-perch/bin/python3 ml/cek_reproduksi_perch.py --n 40
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
ML = REPO / "ml"
LAPORAN = ML / "reports" / "k6_perch" / "reproduksi_embedding.json"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--emb-dir", default=str(ML / "embeddings_perch"))
    ap.add_argument("--manifest", default=str(ML / "data" / "manifest_v2.csv"))
    ap.add_argument("--model-dir", default=str(ML / "models_perch"))
    ap.add_argument("--n", type=int, default=40)
    a = ap.parse_args()

    sys.path.insert(0, str(ML / "data"))
    import tensorflow as tf
    from extract_perch import baca_audio_32k, temukan_kunci_embedding

    emb_dir = Path(a.emb_dir)
    lama = np.load(emb_dir / "embeddings.npy")
    ids = json.loads((emb_dir / "clip_ids.json").read_text())
    idx_per_id = {cid: i for i, cid in enumerate(ids)}

    baris = {r["clip_id"]: r for r in csv.DictReader(open(a.manifest, encoding="utf-8"))}
    tersedia = [c for c in ids if c in baris and (ML / "data" / baris[c]["local_path"]).exists()]
    print(f"klip di embedding lama: {len(ids)}, yang audionya masih ada: {len(tersedia)}")
    if not tersedia:
        print("GAGAL: tidak ada audio yang bisa dicocokkan")
        return 1

    rng = np.random.default_rng(2026)
    pilih = [tersedia[i] for i in rng.choice(len(tersedia), size=min(a.n, len(tersedia)), replace=False)]

    model = tf.saved_model.load(a.model_dir)
    fn = model.signatures["serving_default"]
    kunci = None

    cos, maxdiff, gagal = [], [], []
    for cid in pilih:
        path = ML / "data" / baris[cid]["local_path"]
        try:
            audio = baca_audio_32k(path)
            keluaran = fn(tf.constant(audio.reshape(1, -1)))
            if kunci is None:
                kunci = temukan_kunci_embedding(keluaran)
                print("tensor embedding:", kunci, tuple(keluaran[kunci].shape))
            baru = np.asarray(keluaran[kunci]).reshape(-1).astype(np.float32)
        except Exception as exc:  # noqa: BLE001
            gagal.append({"clip_id": cid, "error": repr(exc)[:200]})
            continue
        ref = lama[idx_per_id[cid]]
        if baru.shape != ref.shape:
            print(f"DIMENSI BEDA: baru {baru.shape} vs lama {ref.shape}")
            hasil = {"status": "DIMENSI BEDA", "dim_baru": int(baru.shape[0]), "dim_lama": int(ref.shape[0])}
            LAPORAN.parent.mkdir(parents=True, exist_ok=True)
            LAPORAN.write_text(json.dumps(hasil, indent=2))
            return 1
        c = float(np.dot(baru, ref) / (np.linalg.norm(baru) * np.linalg.norm(ref) + 1e-12))
        cos.append(c)
        maxdiff.append(float(np.max(np.abs(baru - ref))))

    if not cos:
        print("GAGAL: semua klip gagal dihitung")
        return 1

    cos_arr = np.array(cos)
    hasil = {
        "n_dicek": len(cos),
        "n_gagal": len(gagal),
        "gagal": gagal[:5],
        "cosine_min": round(float(cos_arr.min()), 6),
        "cosine_median": round(float(np.median(cos_arr)), 6),
        "maxdiff_maks": round(float(max(maxdiff)), 6),
        "model_dir": str(Path(a.model_dir).resolve()),
        "n_cocok_cos_ge_0.999": int((cos_arr >= 0.999).sum()),
    }
    hasil["reproduksi"] = "COCOK" if cos_arr.min() >= 0.999 else "TIDAK COCOK"
    LAPORAN.parent.mkdir(parents=True, exist_ok=True)
    LAPORAN.write_text(json.dumps(hasil, indent=2, ensure_ascii=False))
    print(json.dumps(hasil, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
