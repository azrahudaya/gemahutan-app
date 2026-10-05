#!/usr/bin/env bash
# Ekspor snapshot demo GemaHutan: dump PostgreSQL + berkas audio dari MinIO.
# Hasilnya dipakai untuk deploy profil ringan (tanpa worker/TensorFlow di server).
#
# Pakai: ./ops/export_demo_snapshot.sh [folder_tujuan]
set -euo pipefail

OUT_DIR="${1:-$HOME/gemahutan-demo-snapshot}"
STAMP="$(date +%Y%m%d-%H%M)"
TARGET="$OUT_DIR/$STAMP"
mkdir -p "$TARGET"

echo "==> Ekspor database"
docker compose exec -T db pg_dump -U gemahutan -d gemahutan --clean --if-exists \
  > "$TARGET/database.sql"
echo "    $(wc -l < "$TARGET/database.sql") baris SQL"

echo "==> Ekspor objek MinIO (audio rekaman)"
docker run --rm --network "$(docker compose ps --format '{{.Name}}' minio | head -1 | sed 's/-1$//')_default" \
  -v gemahutan_minio-data:/data:ro -v "$TARGET":/out alpine:3 \
  sh -c 'tar -czf /out/minio-data.tar.gz -C /data .' 2>/dev/null || {
    # fallback: volume dapat berbeda nama, cari volume minio yang ada
    VOL=$(docker volume ls --format '{{.Name}}' | grep -i minio | head -1)
    echo "    memakai volume $VOL"
    docker run --rm -v "$VOL":/data:ro -v "$TARGET":/out alpine:3 \
      sh -c 'tar -czf /out/minio-data.tar.gz -C /data .'
  }

cat > "$TARGET/META.txt" <<EOF
Snapshot demo GemaHutan
Dibuat: $(date -Iseconds)
Database: database.sql (pg_dump --clean, schema + data)
Storage : minio-data.tar.gz (isi volume MinIO)
Catatan : snapshot ini berisi hasil inference yang sudah jadi, jadi server demo
          tidak perlu menjalankan worker TensorFlow.
EOF

du -sh "$TARGET"/*
echo "==> Snapshot siap di $TARGET"
