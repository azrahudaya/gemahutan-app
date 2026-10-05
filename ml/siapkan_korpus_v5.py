"""Bangun korpus v5: v3 dengan negatif iNat diganti negatif Xeno-canto.

Satu perubahan saja terhadap v3: klip negatif iNat (3.205) dikeluarkan,
diganti klip negatif XC dari ml/data/manifest_negatif_xc.csv. Tidak menyentuh
checkpoint produksi atau embeddings_v3.

Keluaran:
- ml/embeddings_negatif_xc/ (embedding klip XC negatif, resep sama: 3 detik pertama)
- ml/data/manifest_v5.csv
- ml/data/splits_v5.json
- ml/embeddings_v5/

Data evaluasi TIDAK berubah: split uji lama, pool CV, uji_independen, korpus lapangan.

Jalankan: source .venv/bin/activate && python ml/siapkan_korpus_v5.py
"""
from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
ML = ROOT / "ml"
DATA = ML / "data"

V3_EMB = ML / "embeddings_v3"
NEG_XC_MANIFEST = DATA / "manifest_negatif_xc.csv"
NEG_XC_MANIFEST_NONBURUNG = DATA / "manifest_negatif_nonburung.csv"
NEG_XC_EMB = ML / "embeddings_negatif_xc"
NEG_XC_EXTRACT_MANIFEST = DATA / "manifest_negatif_xc_extract.csv"
OUT_EMB = ML / "embeddings_v5"
OUT_CKPT = ML / "checkpoints_v5"
OUT_MANIFEST = DATA / "manifest_v5.csv"
OUT_SPLITS = DATA / "splits_v5.json"
SPLITS_V3 = DATA / "splits_v3.json"
MANIFEST_LATIH_V3 = DATA / "manifest_latih_produksi.csv"


def tulis_manifest_ekstraksi():
    """Manifest untuk extract_embeddings.py: semua klip diberi label _negative."""
    rows = []
    for man in [NEG_XC_MANIFEST, NEG_XC_MANIFEST_NONBURUNG]:
        if not man.exists():
            continue
        with open(man, newline="") as f:
            for r in csv.DictReader(f):
                rows.append({
                    "clip_id": r["clip_id"],
                    "source": r["source"],
                    "source_url": r["source_url"],
                    "species_scientific": "_negative",
                    "species_common": "_negative",
                    "split": "train",
                    "duration_s": r.get("duration_s", ""),
                    "sample_rate": "",
                    "quality": r.get("quality", ""),
                    "license": r.get("license", ""),
                    "sha256": "",
                    "local_path": r["local_path"],
                })
    with open(NEG_XC_EXTRACT_MANIFEST, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"Manifest ekstraksi: {len(rows)} klip -> {NEG_XC_EXTRACT_MANIFEST}")
    return len(rows)


def ekstrak_embeddings_negatif():
    """Jalankan extract_embeddings.py untuk klip XC negatif.

    Tidak early-return kalau file ada: extract_embeddings.py sendiri yang
    mengecek jumlah klip dan mengekstrak ulang kalau tidak cocok (mis. hasil
    parsial dari jalan sebelumnya).
    """
    ckpt_tmp = ML / "checkpoints_v5_extract"
    ckpt_tmp.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable, str(ML / "data" / "extract_embeddings.py"),
        "--manifest", str(NEG_XC_EXTRACT_MANIFEST),
        "--out-dir", str(NEG_XC_EMB),
        "--ckpt-dir", str(ckpt_tmp),
        "--force",
    ]
    print("Menjalankan:", " ".join(cmd))
    subprocess.run(cmd, check=True, env={**os.environ, "TF_CPP_MIN_LOG_LEVEL": "3"})


def main() -> int:
    if not NEG_XC_MANIFEST.exists():
        print("ERROR: manifest negatif XC belum ada. Jalankan ml/unduh_negatif_xc.py dulu.")
        return 1

    n_neg = tulis_manifest_ekstraksi()
    print(f"Klip negatif XC untuk diekstrak: {n_neg}")
    ekstrak_embeddings_negatif()

    # Muat v3
    emb3 = np.load(V3_EMB / "embeddings.npy")
    lab3 = np.load(V3_EMB / "labels.npy")
    ids3 = json.load(open(V3_EMB / "clip_ids.json"))
    lm3 = json.load(open(V3_EMB / "label_map.json"))
    neg_idx = lm3["_negative"]
    print(f"v3: {emb3.shape[0]} klip, {len(lm3)} kelas, _negative idx {neg_idx}")

    # Muat embedding negatif XC
    embn = np.load(NEG_XC_EMB / "embeddings.npy")
    idsn = json.load(open(NEG_XC_EMB / "clip_ids.json"))
    lmn = json.load(open(NEG_XC_EMB / "label_map.json"))
    print(f"negatif XC: {embn.shape[0]} klip, kelas {len(lmn)}")

    # Buang klip iNat dari v3
    jaga3 = [i for i, c in enumerate(ids3) if not c.startswith("inat")]
    dibuang = len(ids3) - len(jaga3)
    print(f"iNat dibuang dari v3: {dibuang}")

    # Label negatif XC -> indeks _negative di label v3
    labn = np.array([neg_idx] * len(idsn), dtype=lab3.dtype)

    ids = [ids3[i] for i in jaga3] + list(idsn)
    emb = np.vstack([emb3[jaga3], embn]).astype(np.float32)
    lab = np.concatenate([lab3[jaga3], labn])
    print(f"v5 gabungan: {emb.shape[0]} klip")

    OUT_EMB.mkdir(parents=True, exist_ok=True)
    np.save(OUT_EMB / "embeddings.npy", emb)
    np.save(OUT_EMB / "labels.npy", lab)
    json.dump(ids, open(OUT_EMB / "clip_ids.json", "w"))
    json.dump(lm3, open(OUT_EMB / "label_map.json", "w"), indent=2)

    # splits: train = v3 train minus iNat, plus XC negatif; val/uji tidak berubah
    sp3 = json.load(open(SPLITS_V3))
    xc_neg_ids = set(idsn)
    train5 = [c for c in sp3["train"] if not c.startswith("inat")] + sorted(xc_neg_ids)
    splits5 = {
        "train": train5,
        "val": sp3["val"],
        "test": sp3["test"],
        "catatan": ("v3 dengan 3.205 negatif iNat diganti negatif XC; "
                    "val dan uji tidak berubah"),
    }
    json.dump(splits5, open(OUT_SPLITS, "w"), indent=2)
    print(f"splits_v5: latih {len(train5)}, val {len(splits5['val'])}, "
          f"uji {len(splits5['test'])}")
    print(f"verifikasi uji tidak berubah: {splits5['test'] == sp3['test']}")
    print(f"verifikasi val tidak berubah: {splits5['val'] == sp3['val']}")

    # Normalisasi dari train v5 (dibaca save_logreg.py lewat --ckpt-in)
    idx5 = {c: i for i, c in enumerate(ids)}
    tr5 = [idx5[c] for c in train5 if c in idx5]
    mean = emb[tr5].mean(axis=0).astype(np.float32)
    std = emb[tr5].std(axis=0).astype(np.float32)
    std[std < 1e-8] = 1.0
    OUT_CKPT.mkdir(parents=True, exist_ok=True)
    np.savez(OUT_CKPT / "normalization.npz", mean=mean, std=std)
    print(f"normalisasi v5 dari {len(tr5)} klip latih -> {OUT_CKPT}")

    # manifest_v5.csv: salin manifest_latih_produksi tanpa iNat + negatif XC
    rows = []
    if MANIFEST_LATIH_V3.exists():
        with open(MANIFEST_LATIH_V3, newline="") as f:
            for r in csv.DictReader(f):
                if r["clip_id"].startswith("inat"):
                    continue
                rows.append(r)
    with open(NEG_XC_MANIFEST, newline="") as f:
        for r in csv.DictReader(f):
            rows.append({
                "clip_id": r["clip_id"],
                "source": r["source"],
                "license": r["license"],
                "license_url": r["source_url"],
                "sumber_lisensi": "xeno-canto (per rekaman)",
            })
    if NEG_XC_MANIFEST_NONBURUNG.exists():
        with open(NEG_XC_MANIFEST_NONBURUNG, newline="") as f:
            for r in csv.DictReader(f):
                rows.append({
                    "clip_id": r["clip_id"],
                    "source": r["source"],
                    "license": r["license"],
                    "license_url": r["source_url"],
                    "sumber_lisensi": "xeno-canto non-burung (per rekaman)",
                })
    with open(OUT_MANIFEST, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[
            "clip_id", "source", "license", "license_url", "sumber_lisensi"])
        w.writeheader()
        w.writerows(rows)
    print(f"manifest_v5: {len(rows)} baris")

    print("\nSELESAI. Artefak v3 dan checkpoint produksi tidak disentuh.")
    return 0


if __name__ == "__main__":
    sys.exit(main())