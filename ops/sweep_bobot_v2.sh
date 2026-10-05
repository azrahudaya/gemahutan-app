#!/usr/bin/env bash
# Bandingkan beberapa mode pembobotan kelas pada korpus v2.
#
# Latar: bobot "balanced" pada korpus v2 memberi kelas _negative bobot 0,055 dan
# kelas Gallus gallus bobot 38,5, rasio 701 kali. Akibatnya model mengabaikan
# kelas negatif dan akurasi uji turun dari 0,6772 ke 0,6142.
#
# Skrip ini menjalankan beberapa konfigurasi dan mencetak akurasi uji, F1 makro,
# serta recall kelas _negative supaya pilihan bisa diambil dari angka.

set -u
# Skrip ini ada di <root>/ops/, jadi satu tingkat naik sudah root repo.
cd "$(dirname "$0")/.." || exit 1
source .venv/bin/activate

OUT=/tmp/sweep_v2
mkdir -p "$OUT"

jalankan() {
  local nama="$1"; shift
  local dir="$OUT/$nama"
  mkdir -p "$dir"
  echo "=== $nama ==="
  python3 ml/train_v2.py "$@" \
    --out-dir "$dir/ckpt" --report-dir "$dir/rep" --epochs 120 \
    > "$dir/log.txt" 2>&1
  python3 - "$dir/rep/metrics.json" "$nama" <<'PY'
import json, sys
p, nama = sys.argv[1], sys.argv[2]
try:
    m = json.load(open(p))
except Exception as e:
    print(f"{nama:28s} GAGAL: {e}")
    raise SystemExit
neg = [r for r in m["per_species"] if r["kelas"] == "_negative"]
neg = neg[0] if neg else {"recall": 0.0, "f1": 0.0}
lemah = sorted(m["per_species"], key=lambda x: x["f1"])[:3]
print(f"{nama:28s} acc={m['test_acc']:.4f} f1={m['macro_f1']:.4f} "
      f"neg_recall={neg['recall']:.3f} 3_terlemah={[r['kelas'][:12] for r in lemah]}")
PY
}

jalankan "01-balanced"      --class-weight balanced
jalankan "02-sqrt"          --class-weight sqrt
jalankan "03-capped5"       --class-weight capped:5
jalankan "04-capped10"      --class-weight capped:10
jalankan "05-none"          --class-weight none
jalankan "06-sqrt-neg1200"  --class-weight sqrt --maks-negatif 1200
jalankan "07-capped5-neg1200" --class-weight capped:5 --maks-negatif 1200
jalankan "08-capped10-neg2500" --class-weight capped:10 --maks-negatif 2500

echo
echo "=== ringkasan ==="
for d in "$OUT"/*/; do
  n=$(basename "$d")
  python3 - "$d/rep/metrics.json" "$n" <<'PY'
import json, sys
p, nama = sys.argv[1], sys.argv[2]
try:
    m = json.load(open(p))
    neg = [r for r in m["per_species"] if r["kelas"] == "_negative"][0]
    print(f"{nama:30s} acc={m['test_acc']:.4f} f1={m['macro_f1']:.4f} neg_recall={neg['recall']:.3f}")
except Exception as exc:
    print(f"{nama:30s} tidak ada hasil ({exc})")
PY
done
