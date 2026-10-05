#!/usr/bin/env bash
# Backup database dan berkas audio GemaHutan.
#
# Yang dibuat:
#   ops/backups/<tanggal>/database.sql   dump penuh skema + data
#   ops/backups/<tanggal>/minio/         salinan bucket audio
#   ops/backups/<tanggal>/manifest.txt   daftar berkas, ukuran, dan jumlah baris tabel
#
# Pemulihan: lihat ops/RESTORE.md. Dump diuji pulih ke database sementara oleh
# ops/backup_selftest.sh supaya prosedurnya bukan cuma klaim.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

TANGGAL="$(date +%Y%m%d-%H%M%S)"
TUJUAN="${1:-ops/backups/$TANGGAL}"
mkdir -p "$TUJUAN/minio"

echo "backup ke $TUJUAN"

if ! docker compose ps --status running --services | grep -q '^db$'; then
  echo "container db tidak jalan, tidak ada yang bisa di-dump" >&2
  exit 1
fi

docker compose exec -T db pg_dump -U gemahutan -d gemahutan --clean --if-exists \
  > "$TUJUAN/database.sql"
echo "database.sql: $(wc -c < "$TUJUAN/database.sql") byte"

# Salinan bucket audio. MinIO di container ini tidak punya mc, jadi berkasnya
# diunduh lewat gambar api yang sudah punya boto3. Folder tujuan di-mount ke
# container, kalau tidak hasilnya tertulis di dalam container dan hilang.
ABS_TUJUAN="$(cd "$TUJUAN" && pwd)"
docker compose run --rm -T -v "$ABS_TUJUAN/minio:/backup" api python - <<'PY' > "$TUJUAN/minio-daftar.txt"
import os
import sys
from pathlib import Path

import boto3

tujuan = Path("/backup")
s3 = boto3.client(
    "s3",
    endpoint_url=os.getenv("S3_ENDPOINT", "http://minio:9000"),
    aws_access_key_id=os.getenv("S3_ACCESS_KEY", "minioadmin"),
    aws_secret_access_key=os.getenv("S3_SECRET_KEY", "minioadmin"),
    region_name="us-east-1",
)
bucket = os.getenv("S3_BUCKET", "gemahutan-audio")
jumlah = 0
total = 0
paginator = s3.get_paginator("list_objects_v2")
for halaman in paginator.paginate(Bucket=bucket):
    for obj in halaman.get("Contents", []):
        kunci = obj["Key"]
        if kunci.startswith("cache/"):
            # Cache spektrogram bisa dibuat ulang, tidak perlu ikut backup.
            continue
        lokal = tujuan / kunci
        lokal.parent.mkdir(parents=True, exist_ok=True)
        s3.download_file(bucket, kunci, str(lokal))
        jumlah += 1
        total += obj["Size"]
        print(f"{obj['Size']}\t{kunci}")
print(f"# {jumlah} berkas audio, {total} byte (cache spektrogram dilewati)")
PY

{
  echo "tanggal: $TANGGAL"
  echo "database.sql byte: $(wc -c < "$TUJUAN/database.sql")"
  echo "audio byte: $(du -sb "$TUJUAN/minio" | cut -f1)"
  echo "audio berkas: $(find "$TUJUAN/minio" -type f | wc -l)"
  echo "rekaman: $(docker compose exec -T db psql -U gemahutan -d gemahutan -Atc 'select count(*) from recordings')"
  echo "deteksi: $(docker compose exec -T db psql -U gemahutan -d gemahutan -Atc 'select count(*) from detections')"
  echo "spesies: $(docker compose exec -T db psql -U gemahutan -d gemahutan -Atc 'select count(*) from species')"
  echo "lokasi: $(docker compose exec -T db psql -U gemahutan -d gemahutan -Atc 'select count(*) from sites')"
} > "$TUJUAN/manifest.txt"

echo "selesai. Isi $TUJUAN:"
ls -la "$TUJUAN"
