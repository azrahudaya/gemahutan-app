#!/usr/bin/env bash
# Uji kestabilan konfigurasi Perch pada beberapa seed.
#
# Model Perch pada seed 2024 memberi akurasi uji 0,8346 dan best val 0,8661,
# jauh di atas BirdNET pada korpus yang sama. Karena split uji hanya 127 klip,
# kenaikan itu perlu diulang dengan seed lain sebelum dipakai sebagai klaim.
#
# Konfigurasi tetap: embedding Perch 1536 dimensi, tanpa bobot kelas, negatif
# dibatasi 3000.

set -u
cd "$(dirname "$0")/.." || exit 1
source .venv/bin/activate

OUT=/tmp/multiseed_perch
mkdir -p "$OUT"

for seed in 42 123 2024; do
  echo "=== seed $seed ==="
  python3 ml/train_v2.py \
    --emb-dir ml/embeddings_perch --splits ml/data/splits_v2.json \
    --epochs 300 --class-weight none --maks-negatif 3000 --seed "$seed" \
    --out-dir "$OUT/seed_$seed/ckpt" --report-dir "$OUT/seed_$seed/rep" \
    > "$OUT/seed_$seed.log" 2>&1
done

echo
echo "=== SEBARAN PERCH ==="
python3 - "$OUT" <<'PY'
import json, sys
from pathlib import Path
import numpy as np

base = Path(sys.argv[1])
rows = []
for s in (42, 123, 2024):
    p = base / f"seed_{s}" / "rep" / "metrics.json"
    if not p.exists():
        continue
    m = json.load(open(p))
    neg = [r for r in m["per_species"] if r["kelas"] == "_negative"][0]
    rows.append((s, m["test_acc"], m["macro_f1"], neg["recall"]))
    print(f"  seed {s:>5d} acc={m['test_acc']:.4f} f1={m['macro_f1']:.4f} neg_recall={neg['recall']:.3f}")

if rows:
    for i, nama in ((1, "akurasi uji"), (2, "F1 makro"), (3, "recall negatif")):
        a = np.array([r[i] for r in rows])
        print(f"{nama:16s} rata={a.mean():.4f} simpang={a.std():.4f} min={a.min():.4f} maks={a.max():.4f}")
PY
