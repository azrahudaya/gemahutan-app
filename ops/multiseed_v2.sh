#!/usr/bin/env bash
# Uji kestabilan konfigurasi terbaik pada beberapa seed.
#
# Konfigurasi terbaik dari sweep: korpus v2, tanpa bobot kelas, negatif dibatasi
# 3000. Angka uji 0,7165 baru dari satu seed, dan split uji hanya 127 klip,
# sehingga kenaikan itu belum sah sebelum diulang dengan seed lain.
#
# Skrip ini melatih konfigurasi yang sama dengan tiga seed dan melaporkan
# sebaran akurasi uji, F1 makro, dan recall kelas _negative.

set -u
cd "$(dirname "$0")/.." || exit 1
source .venv/bin/activate

OUT=/tmp/multiseed_v2
mkdir -p "$OUT"

for seed in 42 123 2024; do
  echo "=== seed $seed ==="
  python3 ml/train_v2.py \
    --epochs 300 --class-weight none --maks-negatif 3000 \
    --seed "$seed" \
    --out-dir "$OUT/seed_$seed/ckpt" --report-dir "$OUT/seed_$seed/rep" \
    > "$OUT/seed_$seed.log" 2>&1
  python3 - "$OUT/seed_$seed/rep/metrics.json" "$seed" <<'PY'
import json, sys
try:
    m = json.load(open(sys.argv[1]))
    neg = [r for r in m["per_species"] if r["kelas"] == "_negative"][0]
    print(f"  seed {sys.argv[2]:>5s} acc={m['test_acc']:.4f} f1={m['macro_f1']:.4f} neg_recall={neg['recall']:.3f}")
except Exception as e:
    print(f"  seed {sys.argv[2]} GAGAL: {e}")
PY
done

echo
echo "=== SEBARAN ==="
python3 - "$OUT" <<'PY'
import json, sys
from pathlib import Path
import numpy as np

base = Path(sys.argv[1])
acc, f1, neg = [], [], []
for d in sorted(base.glob("seed_*/rep/metrics.json")):
    m = json.load(open(d))
    acc.append(m["test_acc"])
    f1.append(m["macro_f1"])
    neg.append([r for r in m["per_species"] if r["kelas"] == "_negative"][0]["recall"])

if not acc:
    print("tidak ada hasil")
else:
    for nama, nilai in (("akurasi uji", acc), ("F1 makro", f1), ("recall negatif", neg)):
        a = np.array(nilai)
        print(f"{nama:16s} rata-rata={a.mean():.4f} simpangan={a.std():.4f} "
              f"min={a.min():.4f} maks={a.max():.4f}")
PY
