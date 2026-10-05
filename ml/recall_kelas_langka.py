"""Recall per kelas pada set uji independen, membandingkan dua checkpoint.

Ini ukuran yang paling tepat sasaran: tujuan menambah klip kelas langka adalah
menaikkan recall kelas-kelas itu, dan set uji independen punya sampel lebih besar
dari 3 klip di split uji lama.
"""
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

CACHE = ROOT / "ml/data/uji_independen/embedding_cache"
INDEP = ROOT / "ml/data/uji_independen"
lm = json.load(open(ROOT / "ml/embeddings_v2/label_map.json"))
inv = {v: k for k, v in lm.items()}

kelas_per_clip = {}
with (INDEP / "manifest.csv").open() as fh:
    for r in csv.DictReader(fh):
        if r["species_scientific"] in lm:
            kelas_per_clip[r["clip_id"]] = lm[r["species_scientific"]]

data = []
for f in sorted(CACHE.glob("*.npy")):
    if f.stem in kelas_per_clip:
        data.append((f.stem, kelas_per_clip[f.stem], np.load(f)))

from ml.model_loader import muat  # noqa: E402

LANGKA = ["Dicrurus macrocercus", "Gallus gallus", "Chalcophaps indica",
          "Arachnothera longirostra", "Prinia familiaris", "Hirundo tahitica",
          "Rhipidura javanica", "Lonchura punctulata", "Merops philippinus",
          "Haliastur indus"]

hasil = {}
for nama_ckpt in ("checkpoints", "checkpoints_logreg_langka"):
    d = ROOT / "ml" / nama_ckpt
    if not (d / "best_model.npz").exists():
        continue
    model, mean, std = muat(d)
    benar = defaultdict(int)
    total = defaultdict(int)
    for _cid, kelas, feats in data:
        X = ((feats - mean) / std).astype(np.float32)
        probs = model.forward(X)
        pred = int(np.argmax(probs[int(np.argmax(probs.max(axis=1)))]))
        total[kelas] += 1
        if pred == kelas:
            benar[kelas] += 1
    hasil[nama_ckpt] = (benar, total)

print(f"klip: {len(data)}")
print()
print(f"{'spesies':<30} {'n':>4} {'terpasang':>10} {'latih ulang':>12} {'selisih':>9}")
print("-" * 70)
for nama in LANGKA:
    k = lm.get(nama)
    if k is None:
        continue
    n = hasil.get("checkpoints", ({}, {}))[1].get(k, 0)
    if n == 0:
        continue
    a = hasil["checkpoints"][0].get(k, 0) / n
    b = hasil.get("checkpoints_logreg_langka", ({}, {}))[0].get(k, 0) / n
    tanda = "+" if b - a > 0 else ("" if b == a else "")
    print(f"{nama:<30} {n:>4} {a:>10.4f} {b:>12.4f} {tanda}{b - a:>8.4f}")

print()
tot_a = sum(hasil["checkpoints"][0].values()) / max(1, sum(hasil["checkpoints"][1].values()))
if "checkpoints_logreg_langka" in hasil:
    tot_b = sum(hasil["checkpoints_logreg_langka"][0].values()) / sum(hasil["checkpoints_logreg_langka"][1].values())
    print(f"keseluruhan (jendela paling yakin): terpasang {tot_a:.4f} -> latih ulang {tot_b:.4f}")
