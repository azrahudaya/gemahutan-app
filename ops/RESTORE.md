# Pemulihan GemaHutan

Prosedur ini dipakai kalau database atau berkas audio hilang. Urutannya:
pulihkan database, pulihkan audio, cek aplikasi.

## 1. Siapkan backup

    make backup

Hasilnya di `ops/backups/<tanggal>/`:

    database.sql        dump skema dan data (pg_dump --clean --if-exists)
    minio/              salinan berkas audio, tanpa cache spektrogram
    minio-daftar.txt    daftar berkas dan ukurannya
    manifest.txt        jumlah baris tabel utama saat backup dibuat

Uji dulu bahwa dump benar-benar bisa dipulihkan sebelum diandalkan:

    bash ops/backup_selftest.sh

Uji itu memulihkan dump ke database sementara `gemahutan_restore_uji`,
membandingkan jumlah baris delapan tabel utama, lalu menghapus database uji.
Kalau ada tabel yang jumlahnya beda, backup belum layak dipakai.

## 2. Pulihkan database

Hentikan penulisan dulu supaya tidak ada data setengah jalan:

    docker compose stop api worker

Pulihkan dump (berisi `--clean`, jadi tabel lama diganti):

    docker compose exec -T db psql -U gemahutan -d gemahutan -v ON_ERROR_STOP=1 \
      < ops/backups/<tanggal>/database.sql

Kalau database belum ada sama sekali, buat dulu:

    docker compose exec -T db psql -U gemahutan -d postgres -c "create database gemahutan;"
    docker compose exec -T db psql -U gemahutan -d gemahutan -c "create extension if not exists postgis;"

Lalu jalankan migrasi untuk memastikan skema sesuai versi kode terakhir:

    make migrate

## 3. Pulihkan audio

Berkas audio masuk ke bucket MinIO `gemahutan-audio`. Gambar api sudah punya
boto3, jadi pemulihannya lewat container dengan folder backup di-mount:

    ABS="$(cd ops/backups/<tanggal> && pwd)"
    docker compose run --rm -T -v "$ABS/minio:/backup" api python - <<'PY'
    import os
    from pathlib import Path
    import boto3
    s3 = boto3.client(
        "s3",
        endpoint_url=os.getenv("S3_ENDPOINT", "http://minio:9000"),
        aws_access_key_id=os.getenv("S3_ACCESS_KEY", "minioadmin"),
        aws_secret_access_key=os.getenv("S3_SECRET_KEY", "minioadmin"),
        region_name="us-east-1",
    )
    bucket = os.getenv("S3_BUCKET", "gemahutan-audio")
    akar = Path("/backup")
    jumlah = 0
    for berkas in akar.rglob("*"):
        if berkas.is_file():
            kunci = str(berkas.relative_to(akar))
            s3.upload_file(str(berkas), bucket, kunci)
            jumlah += 1
    print(f"{jumlah} berkas audio dipulihkan")
    PY

Nyalakan kembali aplikasi:

    docker compose start api worker

## 4. Periksa hasilnya

    make health
    curl -s http://localhost:8000/healthz | python -m json.tool
    python3 ops/security_check.py
    python3 ops/e2e_clickthrough.py

Yang harus terlihat: `/healthz` melaporkan db, redis, storage, dan worker sehat,
spektrogram rekaman terbuka (berarti audio benar-benar ada di bucket), dan
click-through selesai tanpa console error.

## Catatan

- Cache spektrogram di bucket sengaja tidak ikut backup, karena bisa dibuat ulang
  dari audio. Kalau ikut, ukuran backup membengkak tanpa manfaat.
- Ambang spesies ada di database dan di `ml/reports/thresholds.json`. Setelah
  pemulihan, jalankan `make sync-thresholds` supaya keduanya sama lagi.
