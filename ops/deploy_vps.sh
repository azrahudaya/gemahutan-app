#!/usr/bin/env bash
# Deploy satu perintah ke VPS produksi GemaHutan.
#
# Alur: rsync repo (dengan saringan di deploy/rsync-filter.txt dan
# deploy/rsync-kecuali.txt) ke server, build, nyalakan stack, lalu tunggu
# /healthz mengembalikan 200 dan cetak status layanan.
#
# deploy/.env.prod TIDAK ikut terkirim kecuali diberi argumen --kirim-env,
# supaya rahasia produksi tidak tertimpa/terbaca dari laptop.
#
# Akses server memakai pengguna gemahutan (bukan root) + sudo. Root SSH sudah
# dinonaktifkan.
#
# Pakai:
#   bash ops/deploy_vps.sh                 # deploy tanpa kirim .env.prod
#   bash ops/deploy_vps.sh --kirim-env     # deploy + kirim deploy/.env.prod
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REMOTE="${REMOTE:-gemahutan@213.163.194.131}"
REMOTE_DIR="${REMOTE_DIR:-/opt/gemahutan}"
PROFILE="pekerja"
COMPOSE="sudo docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env.prod --profile $PROFILE"

KIRIM_ENV=0
if [ "${1:-}" = "--kirim-env" ]; then
  KIRIM_ENV=1
fi

cd "$REPO_DIR"

echo "==> 1/5 rsync repo ke $REMOTE:$REMOTE_DIR"
rsync -az --delete \
  --filter="merge deploy/rsync-filter.txt" \
  --exclude-from="deploy/rsync-kecuali.txt" \
  "$REPO_DIR/" "$REMOTE:$REMOTE_DIR/"

if [ "$KIRIM_ENV" = "1" ]; then
  echo "==> kirim deploy/.env.prod (eksplisit --kirim-env)"
  rsync -az "$REPO_DIR/deploy/.env.prod" "$REMOTE:$REMOTE_DIR/deploy/.env.prod"
else
  echo "==> .env.prod TIDAK dikirim (pakai --kirim-env kalau memang perlu)"
fi

echo "==> 2/5 pastikan /etc/docker/daemon.json sudah membatasi log"
ssh "$REMOTE" "test -f /etc/docker/daemon.json && echo '  daemon.json ada' || echo '  PERINGATAN: daemon.json belum ada'"

echo "==> 3/5 build + nyalakan stack"
ssh "$REMOTE" "cd '$REMOTE_DIR' && $COMPOSE up -d --build"

echo "==> 3b/5 pasang ulang caddy (bind mount menunjuk inode lama setelah rsync --delete)"
ssh "$REMOTE" "cd '$REMOTE_DIR' && $COMPOSE up -d --force-recreate caddy"

echo "==> 4/5 tunggu /healthz 200 (maks 180 detik)"
ssh "$REMOTE" "cd '$REMOTE_DIR' && bash -s" <<'BASH'
set -euo pipefail
for i in $(seq 1 60); do
  kode=$(curl -s -o /dev/null -w '%{http_code}' https://gemahutan.site/healthz || true)
  if [ "$kode" = "200" ]; then
    echo "  /healthz -> 200 (setelah ~$((i*3)) detik)"
    exit 0
  fi
  sleep 3
done
echo "  /healthz TIDAK mencapai 200 dalam 180 detik" >&2
exit 1
BASH

echo "==> 5/5 status layanan"
ssh "$REMOTE" "cd '$REMOTE_DIR' && $COMPOSE ps --format 'table {{.Name}}\t{{.State}}\t{{.Health}}'"

echo "==> 6/6 cek bundel JS bebas localhost:8000 (regresi W-35)"
ssh "$REMOTE" "cd '$REMOTE_DIR' && bash -s" <<'BASH'
set -euo pipefail
html=$(curl -s https://gemahutan.site/)
ketemu=0
for url in $(echo "$html" | grep -oE '/_next/static/chunks/[^"]+\.js' | sort -u); do
  if curl -s "https://gemahutan.site$url" | grep -q 'localhost:8000'; then
    echo "  GAGAL: $url masih memuat localhost:8000" >&2
    ketemu=1
  fi
done
if [ "$ketemu" = "1" ]; then
  echo "  Deploy GAGAL: bundel JS memuat localhost:8000 (NEXT_PUBLIC_API_URL memakai ||)" >&2
  exit 1
fi
echo "  bersih: tidak ada localhost:8000 di bundel JS"
BASH

echo "==> Selesai. https://gemahutan.site"
