# Pulihkan backup produksi GemaHutan

Prosedur untuk memulihkan backup yang dibuat `ops/backup_prod.sh` (pg_dump +
salinan bucket MinIO, dikompres dan dienkripsi age). Jalankan di server produksi
sebagai `root`, dari `/opt/gemahutan`.

PENTING: jangan pernah memulihkan ke database produksi `gemahutan` tanpa
persetujuan. Selalu uji dulu ke database sementara `gemahutan_pulih`.

## 1. Siapkan backup terenkripsi

Backup tersimpan di `/var/backups/gemahutan/<tanggal>.tar.gz.age` (dan mungkin
juga di tujuan offsite lewat rclone). Kunci privat age ada di
`/etc/gemahutan/backup_age.key` (mode 600) dan juga disimpan terpisah oleh
pemilik.

Dekripsi dan ekstrak:

    umask 077
    mkdir -p /var/backups/gemahutan/pulih
    cd /var/backups/gemahutan/pulih
    age -d -i /etc/gemahutan/backup_age.key \
        /var/backups/gemahutan/<tanggal>.tar.gz.age > backup.tar.gz
    tar -xzf backup.tar.gz

Hasilnya: `database.sql`, `minio/`, `manifest.txt`.

## 2. Pulihkan database ke database sementara

Buat database uji (kalau belum ada), lalu masukkan dump:

    docker compose -f deploy/docker-compose.prod.yml \
        --env-file deploy/.env.prod --profile pekerja \
        exec -T db psql -U gemahutan -d postgres \
        -c "DROP DATABASE IF EXISTS gemahutan_pulih;"
    docker compose -f deploy/docker-compose.prod.yml \
        --env-file deploy/.env.prod --profile pekerja \
        exec -T db psql -U gemahutan -d postgres \
        -c "CREATE DATABASE gemahutan_pulih;"

Dump berisi `--clean --if-exists`, jadi tabel lama diganti. Masukkan lewat
database uji (bukan produksi):

    docker compose -f deploy/docker-compose.prod.yml \
        --env-file deploy/.env.prod --profile pekerja \
        exec -T db psql -U gemahutan -d gemahutan_pulih -v ON_ERROR_STOP=1 \
        < database.sql

## 3. Bandingkan jumlah baris

    for t in recordings detections species sites users; do
      echo -n "$t: "
      docker compose -f deploy/docker-compose.prod.yml \
        --env-file deploy/.env.prod --profile pekerja \
        exec -T db psql -U gemahutan -d gemahutan_pulih -Atc "select count(*) from $t"
    done

Bandingkan dengan `manifest.txt`. Jumlahnya harus sama.

## 4. Pulihkan audio (kalau perlu)

Unggah kembali isi `minio/` ke bucket. Pakai mc dari host lewat IP kontainer
minio:

    MINIO_IP=$(docker compose -f deploy/docker-compose.prod.yml \
      --env-file deploy/.env.prod --profile pekerja ps -q minio \
      | xargs docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}')
    AK=$(docker compose -f deploy/docker-compose.prod.yml \
      --env-file deploy/.env.prod --profile pekerja exec -T minio printenv MINIO_ROOT_USER | tr -d '\r')
    SK=$(docker compose -f deploy/docker-compose.prod.yml \
      --env-file deploy/.env.prod --profile pekerja exec -T minio printenv MINIO_ROOT_PASSWORD | tr -d '\r')
    mc alias set lokal "http://$MINIO_IP:9000" "$AK" "$SK"
    mc mirror --overwrite minio/ lokal/gemahutan-audio

Cache spektrogram (`cache/`) sengaja tidak ikut backup dan dibuat ulang otomatis.

## 5. Bersihkan

Setelah verifikasi, hapus database uji supaya tidak membebani disk:

    docker compose -f deploy/docker-compose.prod.yml \
        --env-file deploy/.env.prod --profile pekerja \
        exec -T db psql -U gemahutan -d postgres -c "DROP DATABASE gemahutan_pulih;"
    rm -rf /var/backups/gemahutan/pulih
