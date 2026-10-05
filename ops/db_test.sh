#!/usr/bin/env bash
# Siapkan basis data test TERPISAH (gemahutan_test) lalu jalankan test API.
#
# Kenapa harus terpisah: sebelum ini test API berjalan di basis data yang sama
# dengan data demo. Dua akibatnya nyata dan sudah terjadi:
#
# 1. Fixture test login sebagai admin@gemahutan.id dengan sandi `admin123`.
#    Selama test dan dev berbagi basis data, akun dev HARUS memakai sandi lemah
#    itu supaya test hijau. Dengan basis data terpisah, sandi lemah hanya ada di
#    basis data test dan akun dev bisa memakai sandi acak yang kuat.
# 2. Test menumpuk akun, lokasi, dan perangkat di basis data yang dilihat
#    pengguna, dan harus dibersihkan lewat pencocokan awalan nama. Pembersihan
#    berbasis awalan selalu bisa ketinggalan.
#
# Aman dijalankan berulang. Tidak pernah menyentuh basis data `gemahutan`.
#
# Pakai:
#   bash ops/db_test.sh siapkan   # buat/migrasi/seed basis data test
#   bash ops/db_test.sh test      # jalankan pytest di basis data test
#   bash ops/db_test.sh buang     # hapus basis data test
set -euo pipefail

DB_TEST="${DB_TEST:-gemahutan_test}"
DSN_SYNC="postgresql://gemahutan:gemahutan@db:5432/${DB_TEST}"
DSN_ASYNC="postgresql+asyncpg://gemahutan:gemahutan@db:5432/${DB_TEST}"

# Sandi ini SENGAJA sama dengan yang dipakai fixture di apps/api/tests/conftest.py.
# Nilainya hanya berlaku di basis data test yang tidak pernah diekspos, dan
# itulah gunanya memisahkan basis data: sandi lemah tidak lagi bocor ke dev.
SANDI_ADMIN_TEST="admin123"
SANDI_PENELITI_TEST="peneliti123"

psql_postgres() {
  docker compose exec -T db psql -v ON_ERROR_STOP=1 -U gemahutan -d postgres "$@"
}

api_test_env() {
  docker compose exec -T \
    -e DATABASE_URL="${DSN_ASYNC}" \
    -e DATABASE_URL_SYNC="${DSN_SYNC}" \
    -e SEED_ADMIN_PASSWORD="${SANDI_ADMIN_TEST}" \
    -e SEED_RESEARCHER_PASSWORD="${SANDI_PENELITI_TEST}" \
    -e ALLOW_DEMO_SEED=true \
    api "$@"
}

siapkan() {
  echo "== Pastikan basis data ${DB_TEST} ada"
  if psql_postgres -tAc "SELECT 1 FROM pg_database WHERE datname='${DB_TEST}'" | grep -q 1; then
    echo "   sudah ada"
  else
    psql_postgres -c "CREATE DATABASE ${DB_TEST} OWNER gemahutan"
    echo "   dibuat"
  fi

  echo "== PostGIS"
  docker compose exec -T db psql -v ON_ERROR_STOP=1 -U gemahutan -d "${DB_TEST}" \
    -c "CREATE EXTENSION IF NOT EXISTS postgis" >/dev/null
  echo "   siap"

  echo "== Migrasi + seed"
  api_test_env sh -lc 'alembic upgrade head && python -m app.seed'
}

jalankan_test() {
  echo "== pytest di ${DB_TEST}"
  api_test_env python -m pytest tests -q
}

buang() {
  echo "== Hapus ${DB_TEST}"
  psql_postgres -c "DROP DATABASE IF EXISTS ${DB_TEST}"
}

case "${1:-test}" in
  siapkan) siapkan ;;
  test)    siapkan && jalankan_test ;;
  buang)   buang ;;
  *) echo "pakai: $0 {siapkan|test|buang}" >&2; exit 2 ;;
esac
