#!/usr/bin/env bash
# Jalankan perintah panjang di latar dengan status yang BISA DIPERCAYA.
#
# Kenapa ada: audit peninjau 2 Oktober menemukan dua proses dilaporkan
# "completed normally (exit code 0)" padahal Python-nya crash dengan traceback.
# Sebabnya `python ... 2>&1 | tail -20`: exit code yang terlihat adalah milik
# `tail`, bukan milik python. Kalau status proses latar dipakai sebagai tanda
# keberhasilan tanpa membaca isi log, kegagalan seperti itu lolos tanpa terlihat.
#
# Dua pengaman:
#   set -o pipefail  -> exit code pipeline = perintah pertama yang gagal
#   berkas SELESAI   -> exit code python ditulis eksplisit ke disk
#
# Berkas status ditulis ke ops/logs/latar/<nama>.txt dengan tiga baris:
#   RC=<exit code>
#   LOG=<path log>
#   WAKTU=<detik>
# Protokol putus-sambung: baca berkas itu, JANGAN tebak dari daftar proses.
#
# Pakai:
#   bash ml/jalankan_latar.sh <nama> <perintah...>
# Contoh:
#   bash ml/jalankan_latar.sh g_tanpa_k1 .venv/bin/python ml/jalankan_gabungan.py --id g_tanpa_k1

set -o pipefail
set -u

if [ "$#" -lt 2 ]; then
    echo "pakai: bash ml/jalankan_latar.sh <nama> <perintah...>" >&2
    exit 2
fi

NAMA="$1"
shift

AKAR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIR_STATUS="$AKAR/ops/logs/latar"
mkdir -p "$DIR_STATUS"
LOG="/tmp/${NAMA}.log"
STATUS="$DIR_STATUS/${NAMA}.txt"

rm -f "$STATUS"
T0=$(date +%s)

# Jangan pipe keluaran ke apa pun. Semua masuk log, exit code tetap milik
# perintah aslinya.
"$@" > "$LOG" 2>&1
RC=$?

T1=$(date +%s)
{
    echo "RC=$RC"
    echo "LOG=$LOG"
    echo "WAKTU=$((T1 - T0))"
    echo "PERINTAH=$*"
} > "$STATUS"

if [ "$RC" -ne 0 ]; then
    echo "GAGAL rc=$RC, 20 baris terakhir $LOG:" >&2
    tail -20 "$LOG" >&2
fi
exit "$RC"
