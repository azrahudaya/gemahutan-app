#!/bin/bash
set -e

cd /home/fuudaya/Projects/gemahutan

echo "=== S1: Konfirmasi Lunak ==="
docker compose exec -T api python /app/ml/sapu_konfirmasi_lunak.py

echo ""
echo "=== S3: Jendela Bersuara ==="
docker compose exec -T api python /app/ml/extract_jendela_bersuara.py

echo ""
echo "=== S5: Kepala Sigmoid ==="
# Modifikasi model dulu, latih ulang
# Script belum ada, perlu dibuat

echo ""
echo "=== S7: Proksi Data Lapangan Xeno-canto ==="
# Script belum ada, perlu dibuat

echo ""
echo "=== S6: Embedding Perch ==="
# Download dari kagglehub, ekstrak

echo ""
echo "=== S8: Pilih Kandidat Terbaik ==="
# Script belum ada, perlu dibuat
