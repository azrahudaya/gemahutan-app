"""Akurasi per sumber pada split uji besar.

Kenapa perlu: split uji besar (1239 klip) memberi akurasi 0,9411, jauh di atas
0,7874 pada split uji lama (127 klip). Ternyata penyebabnya komposisi, bukan
perbaikan model: split lama 100 persen Xeno-canto, sedangkan split baru hanya
10,7 persen Xeno-canto dan 83 persen dari SEA-Bird, iNaturalist, dan ULM.

Mengutip 0,9411 sebagai capaian akan menyesatkan, karena angka itu didominasi
sumber yang kondisi rekamannya mirip data latih. Yang jujur adalah memecahnya
per sumber dan menyebut komposisinya.
"""
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.metrics import accuracy_score, f1_score, recall_score  # noqa: E402

EMB = ROOT / "ml/embeddings_v2"
CKPT = ROOT / "ml/checkpoints_v2"
SPLITS = ROOT / "ml/data/splits_v2_besar.json"
MAKS_NEGATIF = 3000
SEED = 2024

emb = np.load(EMB / "embeddings.npy")
lab = np.load(EMB / "labels.npy")
ids = json.load(open(EMB / "clip_ids.json"))
label_map = json.load(open(EMB / "label_map.json"))
kelas_neg = label_map["_negative"]
sp = json.load(open(SPLITS))
idx = {c: i for i, c in enumerate(ids)}
norm = np.load(CKPT / "normalization.npz")
mean, std = norm["mean"], norm["std"]

sumber = {}
for r in csv.DictReader(open(ROOT / "ml/data/manifest_v2.csv")):
    sumber[r["clip_id"]] = r.get("source", "?")

rng = np.random.default_rng(SEED)
tr = [idx[c] for c in sp["train"] if c in idx]
ytr = lab[tr]
pos_neg = [i for i, i2 in enumerate(tr) if ytr[i] == kelas_neg]
if len(pos_neg) > MAKS_NEGATIF:
    buang = set(rng.choice(pos_neg, size=len(pos_neg) - MAKS_NEGATIF, replace=False).tolist())
    tr = [v for i, v in enumerate(tr) if i not in buang]
    ytr = np.array([label for i, label in enumerate(ytr) if i not in buang])

Xtr = ((emb[tr] - mean) / std).astype(np.float32)
lr = LogisticRegression(max_iter=3000, C=1.0, class_weight="balanced")
lr.fit(Xtr, ytr)

te_ids = [c for c in sp["test"] if c in idx]
Xte = ((emb[[idx[c] for c in te_ids]] - mean) / std).astype(np.float32)
yte = lab[[idx[c] for c in te_ids]]
pred = lr.predict(Xte)
benar = (pred == yte)

print(f"uji besar: n={len(te_ids)}, akurasi keseluruhan {accuracy_score(yte, pred):.4f}")
print()
print(f"{'sumber':<22} {'n':>6} {'akurasi':>9} {'f1 makro':>9} {'recall_neg':>11}")
print("-" * 62)
per_sumber = defaultdict(list)
for i, c in enumerate(te_ids):
    per_sumber[sumber.get(c, "?")].append(i)
for s in sorted(per_sumber, key=lambda k: -len(per_sumber[k])):
    sel = per_sumber[s]
    y, p = yte[sel], pred[sel]
    print(f"{s:<22} {len(sel):>6} {accuracy_score(y, p):>9.4f} "
          f"{f1_score(y, p, average='macro', zero_division=0):>9.4f} "
          f"{recall_score(y, p, labels=[kelas_neg], average='micro', zero_division=0):>11.4f}")

print()
print("pembanding: split uji lama 127 klip, 100 persen Xeno-canto, akurasi 0,7874")
