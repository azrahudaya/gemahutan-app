"""Bangun korpus v6: v3 + negatif XC (ditambah, bukan mengganti).

Keluaran:
- ml/embeddings_v6/
- ml/data/splits_v6.json
- ml/checkpoints_v6/normalization.npz
- ml/data/manifest_v6.csv

Jalankan: source .venv/bin/activate && python ml/siapkan_korpus_v6.py
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
ML = ROOT / "ml"
DATA = ML / "data"

V3_EMB = ML / "embeddings_v3"
NEG_XC_EMB = ML / "embeddings_negatif_xc"
NEG_XC_MANIFEST = DATA / "manifest_negatif_xc.csv"
NEG_XC_MANIFEST_NONBURUNG = DATA / "manifest_negatif_nonburung.csv"
OUT_EMB = ML / "embeddings_v6"
OUT_CKPT = ML / "checkpoints_v6"
OUT_SPLITS = DATA / "splits_v6.json"
OUT_MANIFEST = DATA / "manifest_v6.csv"
SPLITS_V3 = DATA / "splits_v3.json"
MANIFEST_LATIH_V3 = DATA / "manifest_latih_produksi.csv"


def main() -> int:
    if not NEG_XC_EMB.exists():
        print("ERROR: embeddings_negatif_xc belum ada")
        return 1

    emb3 = np.load(V3_EMB / "embeddings.npy")
    lab3 = np.load(V3_EMB / "labels.npy")
    ids3 = json.loads((V3_EMB / "clip_ids.json").read_text())
    lm3 = json.loads((V3_EMB / "label_map.json").read_text())
    neg_idx = lm3["_negative"]

    embn = np.load(NEG_XC_EMB / "embeddings.npy")
    idsn = json.loads((NEG_XC_EMB / "clip_ids.json").read_text())

    ids3_set = set(ids3)
    idsn_baru = [c for c in idsn if c not in ids3_set]
    idxn = {c: i for i, c in enumerate(idsn)}
    embn_baru = embn[[idxn[c] for c in idsn_baru]].astype(np.float32)

    ids = ids3 + idsn_baru
    emb = np.vstack([emb3.astype(np.float32), embn_baru])
    lab = np.concatenate([lab3, np.array([neg_idx] * len(idsn_baru), dtype=lab3.dtype)])

    OUT_EMB.mkdir(parents=True, exist_ok=True)
    np.save(OUT_EMB / "embeddings.npy", emb)
    np.save(OUT_EMB / "labels.npy", lab)
    (OUT_EMB / "clip_ids.json").write_text(json.dumps(ids))
    (OUT_EMB / "label_map.json").write_text(json.dumps(lm3, indent=2))

    sp3 = json.loads(SPLITS_V3.read_text())
    train6 = sp3["train"] + sorted(idsn_baru)
    splits6 = {
        "train": train6,
        "val": sp3["val"],
        "test": sp3["test"],
        "catatan": "v3 + negatif XC ditambah, val/uji tetap",
    }
    OUT_SPLITS.write_text(json.dumps(splits6, indent=2))

    idx6 = {c: i for i, c in enumerate(ids)}
    tr6 = [idx6[c] for c in train6 if c in idx6]
    mean = emb[tr6].mean(axis=0).astype(np.float32)
    std = emb[tr6].std(axis=0).astype(np.float32)
    std[std < 1e-8] = 1.0
    OUT_CKPT.mkdir(parents=True, exist_ok=True)
    np.savez(OUT_CKPT / "normalization.npz", mean=mean, std=std)

    rows = []
    if MANIFEST_LATIH_V3.exists():
        with MANIFEST_LATIH_V3.open(newline="") as f:
            rows.extend(list(csv.DictReader(f)))
    for src_manifest, sumber in [
        (NEG_XC_MANIFEST, "xeno-canto (per rekaman)"),
        (NEG_XC_MANIFEST_NONBURUNG, "xeno-canto non-burung (per rekaman)"),
    ]:
        if not src_manifest.exists():
            continue
        with src_manifest.open(newline="") as f:
            for r in csv.DictReader(f):
                if r["clip_id"] not in set(idsn_baru):
                    continue
                rows.append(
                    {
                        "clip_id": r["clip_id"],
                        "source": r.get("source", "xeno-canto"),
                        "license": r.get("license", ""),
                        "license_url": r.get("source_url", ""),
                        "sumber_lisensi": sumber,
                    }
                )

    with OUT_MANIFEST.open("w", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["clip_id", "source", "license", "license_url", "sumber_lisensi"],
        )
        w.writeheader()
        w.writerows(rows)

    print(f"v3 awal: {len(ids3)} klip")
    print(f"negatif XC total: {len(idsn)} klip, yang ditambah: {len(idsn_baru)}")
    print(f"v6 total: {len(ids)} klip")
    print(f"splits_v6 latih/val/uji: {len(train6)}/{len(splits6['val'])}/{len(splits6['test'])}")
    print(f"verifikasi val sama v3: {splits6['val'] == sp3['val']}")
    print(f"verifikasi uji sama v3: {splits6['test'] == sp3['test']}")
    print(f"Output: {OUT_EMB}, {OUT_SPLITS}, {OUT_CKPT / 'normalization.npz'}, {OUT_MANIFEST}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
