#!/usr/bin/env bash
# Deploy demo GemaHutan ke VPS kecil dari repo lokal.
#
# Alur: kirim repo + snapshot demo, restore database dan storage, lalu nyalakan
# profil ringan (db, redis, minio, api, web, caddy). Worker TensorFlow tidak
# dijalankan karena RAM VPS dipakai aplikasi produksi lain.
#
# Pakai: ./ops/deploy_demo_vps.sh user@host /path/remote
set -euo pipefail

REMOTE="${1:?Pakai: $0 user@host /path/remote}"
REMOTE_DIR="${2:-/home/ubuntu/gemahutan-demo}"
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SNAPSHOT_DIR="${SNAPSHOT_DIR:-$HOME/gemahutan-demo-snapshot}"

cd "$REPO_DIR"

echo "==> 1/5 Ekspor snapshot demo (database + storage)"
"$REPO_DIR/ops/export_demo_snapshot.sh" "$SNAPSHOT_DIR"
SNAP="$(ls -1d "$SNAPSHOT_DIR"/*/ | tail -1)"
echo "    snapshot: $SNAP"

echo "==> 2/5 Kirim repo dan snapshot ke $REMOTE:$REMOTE_DIR"
ssh "$REMOTE" "mkdir -p '$REMOTE_DIR' '$REMOTE_DIR/snapshot'"
rsync -az --delete \
  --exclude '.git' --exclude '.venv' --exclude 'node_modules' \
  --exclude 'ml/data/audio' --exclude '.next' --exclude 'ml/embeddings/*.npy' \
  "$REPO_DIR"/ "$REMOTE:$REMOTE_DIR/"
rsync -az "$SNAP" "$REMOTE:$REMOTE_DIR/snapshot/"

echo "==> 3/5 Siapkan .env.prod kalau belum ada"
ssh "$REMOTE" "test -f '$REMOTE_DIR/deploy/.env.prod' || { cp '$REMOTE_DIR/deploy/.env.prod.example' '$REMOTE_DIR/deploy/.env.prod'; echo '    .env.prod dibuat dari contoh, ISI DULU nilai domain dan password'; }"

echo "==> 4/5 Nyalakan stack produksi"
ssh "$REMOTE" "cd '$REMOTE_DIR' && docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env.prod up -d --build"

echo "==> 5/5 Restore data demo ke container"
ssh "$REMOTE" "cd '$REMOTE_DIR' && \
  docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env.prod exec -T db \
    psql -U gemahutan -d gemahutan < snapshot/database.sql && \
  docker run --rm -v \$(docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env.prod ps -q minio | head -1 | xargs -I{} echo gemahutan-demo_minio-data):/data alpine:3 sh -c 'rm -rf /data/* && tar -xzf /snapshot/minio-data.tar.gz -C /data' 2>/dev/null || \
  echo '    restore storage: jalankan manual, lihat docs/DEPLOY.md'"

echo "==> Selesai. Cek: curl -s https://DOMAIN/healthz"
