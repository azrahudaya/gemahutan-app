#!/usr/bin/env bash
# Sinkron repo PUBLIK GemaHutan dari snapshot bersih.
#
# Ini SATU-SATUNYA jalur ke repo publik `azrahudaya/gemahutan-app`. Hanya
# dijalankan kalau pemilik/peninjau memintanya (USER_03 blok C). Uji dulu
# dengan --coba.
#
# Alur: salin berkas yang dilacak git ke folder sementara, inisialisasi repo
# baru (commit orphan), pindai rahasia, commit dengan pengarang eksplisit,
# push. Riwayat gemahutan-arsip TIDAK ikut.
#
# Pakai:
#   bash ops/sinkron_publik.sh --coba   # uji pindai + cek pohon, tanpa push
#   bash ops/sinkron_publik.sh          # pindai + commit + push
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PUBLIK_REMOTE="${PUBLIK_REMOTE:-git@github.com:azrahudaya/gemahutan-app.git}"
PUBLIK_PESAN="${PUBLIK_PESAN:-GemaHutan: snapshot $(date -u +%Y-%m-%dT%H:%M:%SZ)}"
AUTHOR_NAME="Azra Hudaya"
AUTHOR_EMAIL="95754136+azrahudaya@users.noreply.github.com"
TEMP_DIR="$(mktemp -d)"
COBA=0
if [ "${1:-}" = "--coba" ]; then
  COBA=1
fi

trap 'rm -rf "$TEMP_DIR"' EXIT

cd "$REPO_DIR"

echo "==> 1/5 salin berkas git ke folder sementara"
git ls-files | while IFS= read -r rel; do
  case "$rel" in
    .artifacts/*) continue ;;
    .hermes/*) continue ;;
    .claude/*) continue ;;
    .env) continue ;;
    deploy/.env.prod) continue ;;
  esac
  mkdir -p "$TEMP_DIR/$(dirname "$rel")"
  cp -a "$rel" "$TEMP_DIR/$rel"
done
echo "    $(git ls-files | wc -l) berkas dilacak git"

echo "==> 2/5 cek pohon commit (tidak boleh ada berkas terlarang)"
TERLARANG=$(find "$TEMP_DIR" \( -name ".hermes" -o -name ".claude" -o -name ".env" -o -name ".env.prod" \) -print)
if [ -n "$TERLARANG" ]; then
  echo "  GAGAL: berkas terlarang ikut tersalin:" >&2
  echo "$TERLARANG" >&2
  exit 1
fi
echo "    bersih"

echo "==> 3/5 inisialisasi repo git (commit orphan)"
git -C "$TEMP_DIR" init -q -b main
git -C "$TEMP_DIR" add -A
GIT_AUTHOR_NAME="$AUTHOR_NAME" GIT_AUTHOR_EMAIL="$AUTHOR_EMAIL" \
GIT_COMMITTER_NAME="$AUTHOR_NAME" GIT_COMMITTER_EMAIL="$AUTHOR_EMAIL" \
  git -C "$TEMP_DIR" commit -q -m "$PUBLIK_PESAN"

if [ "$COBA" = "1" ]; then
  echo "==> MODE --coba: cek pesan, pengarang, dan trailer"
  git -C "$TEMP_DIR" log --format='%an <%ae> | %s%n%(trailers)' -1
  if git -C "$TEMP_DIR" log --format='%an %ae %b' -1 | grep -qi "claude"; then
    echo "  GAGAL: nama claude muncul di log" >&2
    exit 1
  fi
  echo "    tidak ada claude. Selesai (tidak push)."
  exit 0
fi

echo "==> 4/5 pindai rahasia"
python3 "$REPO_DIR/ops/pindai_rahasia.py" --cwd "$TEMP_DIR"

echo "==> 5/5 push ke repo publik"
git -C "$TEMP_DIR" remote add origin "$PUBLIK_REMOTE"
git -C "$TEMP_DIR" push -u origin main
echo "==> Selesai. Repo publik diperbarui."
