#!/usr/bin/env bash
# Cari jumlah klip negatif yang memberi keseimbangan terbaik.
#
# Temuan sementara: korpus v2 menurunkan deteksi palsu dari 0,6484 ke 0,4062,
# tetapi akurasi pada rekaman lapangan juga turun (inat 0,4869 ke 0,3557,
# xc_noisy 0,6625 ke 0,5609). Dugaan: 5612 klip negatif membuat model terlalu
# konservatif sehingga banyak burung nyata ikut ditolak.
#
# Sweep ini menyapu batas jumlah negatif dan mode bobot untuk mencari
# konfigurasi yang menurunkan deteksi palsu tanpa mengorbankan akurasi lapangan.

set -u
cd "$(dirname "$0")/.." || exit 1
source .venv/bin/activate

OUT=/tmp/sweep_neg
mkdir -p "$OUT"

jalankan() {
  local nama="$1"; shift
  local dir="$OUT/$nama"
  mkdir -p "$dir"
  echo "=== $nama ==="
  python3 ml/train_v2.py "$@" \
    --out-dir "$dir/ckpt" --report-dir "$dir/rep" --epochs 150 \
    > "$dir/train.log" 2>&1
  python3 ml/evaluate_field.py --lewati-degradasi \
    --checkpoint-dir "$dir/ckpt" --akhiran "_$nama" \
    > "$dir/eval.log" 2>&1
  python3 - "$dir/rep/metrics.json" "$HOME/Projects/gemahutan/ml/reports/field_metrics_$nama.json" "$nama" <<'PY'
import json, sys
try:
    m = json.load(open(sys.argv[1]))
    f = json.load(open(sys.argv[2]))
except Exception as e:
    print(f"{sys.argv[3]:26s} GAGAL: {e}")
    raise SystemExit
neg = [r for r in m["per_species"] if r["kelas"] == "_negative"][0]
def ambil(k):
    v = f.get(k) or {}
    return v.get("akurasi_top1"), v.get("deteksi_palsu")
print(f"{sys.argv[3]:26s} uji={m['test_acc']:.4f} f1={m['macro_f1']:.4f} "
      f"neg_rec={neg['recall']:.3f} "
      f"inat={ambil('inat')[0]} palsu={ambil('other')[1]} xc={ambil('xc_noisy')[0]}")
PY
}

jalankan "neg1000-none"  --class-weight none --maks-negatif 1000
jalankan "neg2000-none"  --class-weight none --maks-negatif 2000
jalankan "neg3000-none"  --class-weight none --maks-negatif 3000
jalankan "neg1500-capped3" --class-weight capped:3 --maks-negatif 1500
jalankan "neg2500-capped3" --class-weight capped:3 --maks-negatif 2500

echo
echo "=== RINGKASAN ==="
for d in "$OUT"/*/; do
  n=$(basename "$d")
  python3 - "$d/rep/metrics.json" "$HOME/Projects/gemahutan/ml/reports/field_metrics_$n.json" "$n" <<'PY'
import json, sys
try:
    m = json.load(open(sys.argv[1])); f = json.load(open(sys.argv[2]))
    neg = [r for r in m["per_species"] if r["kelas"] == "_negative"][0]
    def ambil(k):
        v = f.get(k) or {}
        return v.get("akurasi_top1"), v.get("deteksi_palsu")
    print(f"{sys.argv[3]:26s} uji={m['test_acc']:.4f} f1={m['macro_f1']:.4f} "
          f"neg_rec={neg['recall']:.3f} inat={ambil('inat')[0]} "
          f"palsu={ambil('other')[1]} xc={ambil('xc_noisy')[0]}")
except Exception as exc:
    print(f"{sys.argv[3]:26s} tidak ada hasil ({exc})")
PY
done
