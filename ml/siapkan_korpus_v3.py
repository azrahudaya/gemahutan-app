"""Simpan artefak korpus v3 (v2 plus klip kelas langka) supaya bisa direproduksi.

`ml/latih_ulang_kelas_langka.py` menggabungkan embedding di memori saja, jadi
evaluator resmi (`ml/evaluate.py`) tidak bisa memakainya. Skrip ini menuliskan
gabungan itu ke disk:

- ml/embeddings_v3/embeddings.npy, labels.npy, clip_ids.json, label_map.json
- ml/data/splits_v3.json (split lama plus klip baru dimasukkan ke latih)
- ml/checkpoints_langka/normalization.npz (mean dan std dari latih gabungan)

Klip kelas langka masuk ke LATIH, bukan ke uji, dan set uji independen tetap di
luar semua berkas ini.
"""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

V2 = ROOT / "ml/embeddings_v2"
LANGKA = ROOT / "ml/embeddings_langka"
OUT_EMB = ROOT / "ml/embeddings_v3"
OUT_CKPT = ROOT / "ml/checkpoints_langka"
SPLITS_OUT = ROOT / "ml/data/splits_v3.json"
SPLITS_IN = ROOT / "ml/data/splits_v2.json"

emb2 = np.load(V2 / "embeddings.npy")
lab2 = np.load(V2 / "labels.npy")
ids2 = json.load(open(V2 / "clip_ids.json"))
lm2 = json.load(open(V2 / "label_map.json"))
inv2 = {v: k for k, v in lm2.items()}

emb3 = np.load(LANGKA / "embeddings.npy")
lab3 = np.load(LANGKA / "labels.npy")
ids3 = json.load(open(LANGKA / "clip_ids.json"))
lm3 = json.load(open(LANGKA / "label_map.json"))
inv3 = {v: k for k, v in lm3.items()}

sudah = set(ids2)
jaga = [i for i, c in enumerate(ids3) if c not in sudah]
lab3_remap = np.array([lm2[inv3[int(lab3[i])]] for i in jaga], dtype=lab2.dtype)
ids3_pakai = [ids3[i] for i in jaga]

ids = ids2 + ids3_pakai
emb = np.vstack([emb2, emb3[jaga]]).astype(np.float32)
lab = np.concatenate([lab2, lab3_remap])

OUT_EMB.mkdir(parents=True, exist_ok=True)
OUT_CKPT.mkdir(parents=True, exist_ok=True)
np.save(OUT_EMB / "embeddings.npy", emb)
np.save(OUT_EMB / "labels.npy", lab)
json.dump(ids, open(OUT_EMB / "clip_ids.json", "w"))
json.dump(lm2, open(OUT_EMB / "label_map.json", "w"), indent=2)

sp = json.load(open(SPLITS_IN))
di_split = set(sp["train"]) | set(sp["val"]) | set(sp["test"])
baru = [c for c in ids3_pakai if c not in di_split]
splits3 = {
    "train": sp["train"] + baru,
    "val": sp["val"],
    "test": sp["test"],
    "catatan": "splits_v2 plus 98 klip kelas langka di latih; uji tidak berubah",
}
json.dump(splits3, open(SPLITS_OUT, "w"), indent=2)

idx = {c: i for i, c in enumerate(ids)}
tr = [idx[c] for c in splits3["train"] if c in idx]
mean = emb[tr].mean(axis=0).astype(np.float32)
std = emb[tr].std(axis=0).astype(np.float32)
std[std < 1e-8] = 1.0
np.savez(OUT_CKPT / "normalization.npz", mean=mean, std=std)

print(f"embeddings_v3 : {emb.shape[0]} klip, {len(lm2)} kelas")
print(f"  dari v2     : {len(ids2)}")
print(f"  dari langka : {len(ids3_pakai)}")
print(f"splits_v3     : latih {len(splits3['train'])}, val {len(splits3['val'])}, uji {len(splits3['test'])}")
print(f"  klip baru di latih: {len(baru)}")
print(f"normalisasi   : dari {len(tr)} klip latih")
print()
print("verifikasi uji tidak berubah:", splits3["test"] == sp["test"])
