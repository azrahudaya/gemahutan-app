#!/usr/bin/env bash
# Pipeline otomatis setelah unduhan negatif XC selesai:
#   1. tunggu unduh_negatif_xc.py berhenti
#   2. unduh negatif non-burung (belalang + kelelawar)
#   3. bangun korpus v5 (ganti negatif iNat -> XC)
#   4. latih + evaluasi + bandingkan dengan produksi
# Log: ml/reports/v5_pipeline.log
set -u
cd "$(dirname "$0")/.." || exit 1
ROOT="$PWD"
LOG="$ROOT/ml/reports/v5_pipeline.log"
mkdir -p "$ROOT/ml/reports"

log() { echo "[$(date -u +%H:%M:%S)] $*" | tee -a "$LOG"; }

set -a; . .env 2>/dev/null; set +a
export TF_CPP_MIN_LOG_LEVEL=3
# shellcheck disable=SC1091
. .venv/bin/activate

log "=== pipeline v5 menunggu unduhan bird selesai ==="
while pgrep -f "ml/unduh_negatif_xc.py" > /dev/null; do sleep 60; done
log "unduhan bird selesai."

JML=$(tail -n +2 "$ROOT/ml/data/manifest_negatif_xc.csv" 2>/dev/null | wc -l)
log "klip negatif burung: $JML"

log "--- unduh negatif non-burung ---"
python ml/unduh_negatif_nonburung.py >> "$LOG" 2>&1 || log "non-burung GAGAL"

log "--- bangun korpus v5 ---"
if python ml/siapkan_korpus_v5.py >> "$LOG" 2>&1; then
  log "korpus v5 selesai"
else
  log "siapkan_korpus_v5 GAGAL"; exit 1
fi

log "--- latih logreg v5 ---"
python ml/save_logreg.py \
  --emb-dir ml/embeddings_v5 \
  --splits ml/data/splits_v5.json \
  --ckpt-in ml/checkpoints_v5 \
  --out-dir ml/checkpoints_logreg_v5 \
  --report-dir ml/reports_logreg_v5 >> "$LOG" 2>&1 || log "latih GAGAL"

log "--- CV bersarang v5 ---"
python ml/evaluasi_bersarang.py \
  --emb-dir ml/embeddings_v5 \
  --splits ml/data/splits_v5.json \
  --out-akhiran _v5 >> "$LOG" 2>&1 || log "CV GAGAL"

log "--- bandingkan v5 vs produksi ---"
python ml/bandingkan_v5.py >> "$LOG" 2>&1 || log "bandingkan GAGAL"

log "=== pipeline v5 selesai ==="