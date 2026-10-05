#!/usr/bin/env bash
# Uji bahwa dump hasil backup benar-benar bisa dipulihkan.
#
# Prosedurnya dipulihkan ke database sementara di server yang sama, jumlah baris
# tabel utama dibandingkan dengan database asli, lalu database uji dihapus.
# Tanpa uji ini, "ada backup" hanya berarti ada berkas, bukan ada pemulihan.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

DUMP="${1:-}"
if [ -z "$DUMP" ]; then
  DUMP="$(ls -d ops/backups/*/ | tail -1)database.sql"
fi
if [ ! -f "$DUMP" ]; then
  echo "dump tidak ditemukan: $DUMP" >&2
  exit 1
fi

UJI="gemahutan_restore_uji"
echo "menguji dump: $DUMP"

psql_() { docker compose exec -T db psql -U gemahutan "$@"; }

psql_ -d postgres -c "drop database if exists $UJI;" >/dev/null
psql_ -d postgres -c "create database $UJI;" >/dev/null

if ! psql_ -d "$UJI" -v ON_ERROR_STOP=1 < "$DUMP" > /tmp/restore_uji.log 2>&1; then
  echo "pemulihan gagal, 20 baris terakhir log:" >&2
  tail -20 /tmp/restore_uji.log >&2
  psql_ -d postgres -c "drop database if exists $UJI;" >/dev/null || true
  exit 1
fi

TABEL="users species sites devices recordings detections acoustic_indices jobs"
gagal=0
for t in $TABEL; do
  asli="$(psql_ -d gemahutan -Atc "select count(*) from $t")"
  uji="$(psql_ -d "$UJI" -Atc "select count(*) from $t" 2>/dev/null || echo 'tabel tidak ada')"
  if [ "$asli" = "$uji" ]; then
    echo "  $t: $asli = $uji ok"
  else
    echo "  $t: asli $asli, hasil pulih $uji BEDA"
    gagal=$((gagal + 1))
  fi
done

psql_ -d postgres -c "drop database if exists $UJI;" >/dev/null

if [ "$gagal" -ne 0 ]; then
  echo "$gagal tabel tidak cocok, backup tidak bisa diandalkan"
  exit 1
fi
echo "semua tabel cocok, dump bisa dipulihkan"
