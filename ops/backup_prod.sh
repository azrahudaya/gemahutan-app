#!/usr/bin/env bash
# Backup produksi GemaHutan: pg_dump + salinan bucket MinIO, dikompres lalu
# dienkripsi dengan age, disimpan 14 hari. Ditujukan untuk dijalankan di server
# produksi dari /opt/gemahutan lewat cron (02.30 WIB).
#
# Kredensial tujuan offsite (B2/R2) dibaca dari /etc/gemahutan/backup.env kalau
# sudah ada. Selama belum ada, backup disimpan LOKAL di /var/backups/gemahutan
# dengan catatan bahwa ini belum aman (satu disk yang sama dengan produksi).
#
# Kunci age publik dibaca dari /opt/gemahutan/ops/backup_age.pub. Kunci privat
# TIDAK dibutuhkan untuk membuat backup (hanya untuk memulihkan).
set -euo pipefail

COMPOSE="docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env.prod --profile pekerja"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/gemahutan}"
RETENSI_HARI="${RETENSI_HARI:-14}"
USIA_PUB="${USIA_PUB:-/opt/gemahutan/ops/backup_age.pub}"
LOG="${LOG:-/var/log/gemahutan-backup.log}"
NOTIF_ENV="/etc/gemahutan/notif.env"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
STAMP="$BACKUP_DIR/$TIMESTAMP"
WORK="$BACKUP_DIR/.kerja-$TIMESTAMP"

log() { echo "[$(date '+%F %T')] $*" >> "$LOG"; }

kirim_email_gagal() {
  # Kirim email notifikasi kegagalan. Kredensial dari /etc/gemahutan/notif.env.
  if [ ! -f "$NOTIF_ENV" ]; then
    log "backup GAGAL, tapi notif.env belum ada sehingga email tidak dikirim"
    return 0
  fi
  # Baca kredensial tanpa mencetaknya.
  set -a
  # shellcheck disable=SC1090
  . "$NOTIF_ENV"
  set +a
  if [ -z "${SMTP_USER:-}" ] || [ -z "${SMTP_APP_PASSWORD:-}" ] || [ -z "${NOTIF_KE:-}" ]; then
    log "backup GAGAL, tapi notif.env tidak lengkap sehingga email tidak dikirim"
    return 0
  fi
  python3 - "$1" <<'PY'
import os, smtplib, sys
from email.message import EmailMessage
pesan = sys.argv[1]
user = os.environ["SMTP_USER"]
sandi = os.environ["SMTP_APP_PASSWORD"]
ke = os.environ["NOTIF_KE"]
msg = EmailMessage()
msg["Subject"] = "[GemaHutan] Backup produksi GAGAL"
msg["From"] = user
msg["To"] = ke
msg.set_content(pesan)
with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as s:
    s.starttls()
    s.login(user, sandi)
    s.send_message(msg)
PY
  log "email kegagalan backup dikirim ke ${NOTIF_KE:-'(penerima)'}"
}

# Nama langkah yang sedang berjalan, dipakai trap ERR untuk melaporkan langkah
# yang gagal. Diperbarui sebelum tiap tahap.
LANGKAH="persiapan"
EMAIL_TRAP_TERKIRIM=0
trap '
  rc=$?
  if [ "$EMAIL_TRAP_TERKIRIM" = "0" ]; then
    EMAIL_TRAP_TERKIRIM=1
    kirim_email_gagal "Backup produksi GAGAL pada langkah \"${LANGKAH}\" (kode keluar $rc) pada $TIMESTAMP. Lihat $LOG." || true
  fi
  rm -rf "$WORK" 2>/dev/null || true
  exit "$rc"
' ERR

log "=== mulai backup $TIMESTAMP ==="

mkdir -p "$WORK" "$BACKUP_DIR"
cd /opt/gemahutan

# 1. pg_dump database produksi (dari kontainer db).
LANGKAH="pg_dump"
log "pg_dump"
if ! $COMPOSE exec -T db pg_dump -U gemahutan -d gemahutan --clean --if-exists > "$WORK/database.sql" 2>>"$LOG"; then
  log "GAGAL: pg_dump"
  kirim_email_gagal "pg_dump produksi gagal pada $TIMESTAMP. Lihat $LOG."
  rm -rf "$WORK"
  exit 1
fi
DB_ROWS=""
DB_ROWS="$($COMPOSE exec -T db psql -U gemahutan -d gemahutan -Atc 'select count(*) from recordings')" || DB_ROWS="?"
log "database.sql $(wc -c < "$WORK/database.sql") byte, recordings=$DB_ROWS"

# 2. Salin bucket MinIO lewat mc mirror. mc sudah terpasang di host; akses MinIO
#    lewat IP kontainer di network internal supaya port 9000 tidak perlu di-expose.
LANGKAH="mc mirror"
log "mc mirror"
# Bucket kosong tidak membuat folder saat mc mirror, jadi pastikan dulu folder
# tujuannya ada supaya `find` di bawah tidak gagal (ini penyebab backup gagal
# sejak 3 Oktober).
mkdir -p "$WORK/minio"
MINIO_IP="$($COMPOSE ps -q minio | xargs -r docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' 2>/dev/null)"
S3_ACCESS_KEY="$($COMPOSE exec -T minio printenv MINIO_ROOT_USER | tr -d '\r')"
S3_SECRET_KEY="$($COMPOSE exec -T minio printenv MINIO_ROOT_PASSWORD | tr -d '\r')"
if [ -z "$MINIO_IP" ]; then
  log "GAGAL: tidak bisa menentukan IP kontainer minio"
  kirim_email_gagal "Tidak bisa menentukan IP kontainer minio pada $TIMESTAMP."
  rm -rf "$WORK"
  exit 1
fi
if ! mc alias set lokal "http://$MINIO_IP:9000" "$S3_ACCESS_KEY" "$S3_SECRET_KEY" >/dev/null 2>>"$LOG"; then
  log "GAGAL: mc alias set"
  kirim_email_gagal "mc alias set gagal pada $TIMESTAMP."
  rm -rf "$WORK"
  exit 1
fi
if ! mc mirror --overwrite --exclude "cache/*" "lokal/gemahutan-audio" "$WORK/minio" >/dev/null 2>>"$LOG"; then
  log "GAGAL: mc mirror"
  kirim_email_gagal "mc mirror bucket MinIO gagal pada $TIMESTAMP. Lihat $LOG."
  rm -rf "$WORK"
  exit 1
fi
MINIO_FILES="$(find "$WORK/minio" -type f | wc -l)"
log "minio: $MINIO_FILES berkas"

# 3. Manifest jumlah baris tabel utama.
LANGKAH="manifest"
{
  echo "tanggal: $TIMESTAMP"
  echo "database.sql byte: $(wc -c < "$WORK/database.sql")"
  echo "audio berkas: $MINIO_FILES"
  for t in recordings detections species sites users; do
    n="$($COMPOSE exec -T db psql -U gemahutan -d gemahutan -Atc "select count(*) from $t" 2>/dev/null || echo '?')"
    echo "$t: $n"
  done
} > "$WORK/manifest.txt"
log "manifest dibuat"

# 4. Kompres dan enkripsi dengan age.
LANGKAH="kompres + enkripsi age"
log "kompres + enkripsi age"
if ! tar -C "$WORK" -czf "$WORK/backup.tar.gz" database.sql minio manifest.txt 2>>"$LOG"; then
  log "GAGAL: kompres"
  kirim_email_gagal "Kompres backup gagal pada $TIMESTAMP. Lihat $LOG."
  rm -rf "$WORK"
  exit 1
fi
if [ ! -f "$USIA_PUB" ]; then
  log "GAGAL: kunci publik age tidak ada di $USIA_PUB"
  kirim_email_gagal "Kunci publik age tidak ditemukan pada $TIMESTAMP."
  rm -rf "$WORK"
  exit 1
fi
age -r "$(cut -d' ' -f2 "$USIA_PUB" | tail -1)" -o "$STAMP.tar.gz.age" "$WORK/backup.tar.gz" 2>>"$LOG"
AGE_SIZE="$(wc -c < "$STAMP.tar.gz.age")"
log "backup terenkripsi: $STAMP.tar.gz.age ($AGE_SIZE byte)"

# 5. Kirim offsite kalau kredensial B2/R2 sudah ada; kalau belum, simpan lokal saja.
LANGKAH="kirim offsite"
if [ -f /etc/gemahutan/backup.env ]; then
  log "backup.env ada, coba kirim offsite via rclone"
  # shellcheck disable=SC1091
  . /etc/gemahutan/backup.env
  if [ -n "${RCLONE_REMOTE:-}" ]; then
    if rclone copy "$STAMP.tar.gz.age" "$RCLONE_REMOTE" 2>>"$LOG"; then
      log "offsite OK ke $RCLONE_REMOTE"
    else
      log "offsite GAGAL, tetap disimpan lokal"
      kirim_email_gagal "Kirim offsite backup GAGAL pada $TIMESTAMP. Backup tetap tersimpan lokal."
    fi
  fi
else
  log "backup.env BELUM ada: backup hanya disimpan LOKAL (belum aman, satu disk dengan produksi)"
fi

# 6. Retensi 14 hari (berdasarkan mtime).
LANGKAH="retensi"
log "retensi $RETENSI_HARI hari"
find "$BACKUP_DIR" -maxdepth 1 -name '*.tar.gz.age' -mtime +"$RETENSI_HARI" -delete 2>>"$LOG" || true
find "$BACKUP_DIR" -maxdepth 1 -name '.kerja-*' -type d -mmin +60 -exec rm -rf {} + 2>>"$LOG" || true

rm -rf "$WORK"
log "=== selesai backup $TIMESTAMP ==="
echo "$STAMP.tar.gz.age"
