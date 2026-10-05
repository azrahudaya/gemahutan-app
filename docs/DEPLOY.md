# Deploy Guide -- GemaHutan

## Prasyarat
- Docker + Docker Compose v2
- Git
- 4 GB RAM minimum (untuk BirdNET inference)

## Quick Start (Lokal)

```bash
git clone https://github.com/azrahudaya/gemahutan.git
cd gemahutan
cp .env.example .env
docker compose up -d
```

Tunggu semua container healthy (~1-2 menit):
```bash
docker compose ps
curl http://localhost:8000/healthz
```

Akses:
- Frontend: http://localhost:3001
- API: http://localhost:8000
- API docs: http://localhost:8000/docs
- MinIO console: http://localhost:9001 (minioadmin/minioadmin)

## Seed Data

```bash
docker compose exec api alembic upgrade head
docker compose exec api python -m app.seed        # spesies, lokasi, user dasar
docker compose exec api python -m app.seed_demo   # 8 rekaman demo dari klip Xeno-canto asli
```

`app.seed_demo` benar-benar mengunggah audio ke MinIO lalu memasukkan job ke
antrean, jadi deteksi dan indeks yang muncul adalah hasil inference worker.
Pakai `--purge-orphans` untuk membersihkan baris rekaman yang berkas audionya
sudah tidak ada di storage.

## Akun Default (lokal saja)

`app.seed` membuat akun contoh `admin@gemahutan.id` dan `peneliti@gemahutan.id` dengan sandi
contoh. Ini hanya untuk laptop pengembang. Server produksi tidak memakai `seed_demo` dan
tidak punya akun contoh.

## Produksi (gemahutan.site)

Keadaan 3 Oktober 2026:

| Hal | Isi |
|---|---|
| Server | VPS 4 vCPU, 7,7 GB RAM, 99 GB disk, Ubuntu |
| Akses | SSH sebagai pengguna `gemahutan` (sudo), alamat di `ops/deploy_vps.sh`. Login root lewat SSH dimatikan |
| Folder | `/opt/gemahutan` |
| Stack | `deploy/docker-compose.prod.yml --env-file deploy/.env.prod --profile pekerja` |
| HTTPS | Caddy (`deploy/Caddyfile`), CSP, `www` dialihkan ke domain utama |
| Rahasia | `deploy/.env.prod` (mode 600, tidak pernah dicetak), `/etc/gemahutan/*.env` |
| Mesin model | `INFERENCE_ENGINE=cascade` |

### Deploy

```bash
bash ops/deploy_vps.sh              # rsync, build, up, tunggu /healthz 200
bash ops/deploy_vps.sh --kirim-env  # sama, sekaligus mengirim deploy/.env.prod
```

Yang dikirim diatur `deploy/rsync-filter.txt` dan `deploy/rsync-kecuali.txt` (sekitar 43 MB,
bukan seluruh `ml/`). Worker butuh `ml/embeddings/label_map.json` dan checkpoint aktif; kalau
salah satunya tidak terkirim, worker jatuh ke BirdNET saja.

Repo publik `azrahudaya/gemahutan` hanya diperbarui lewat `bash ops/sinkron_publik.sh`
(pakai `--coba` untuk pindai tanpa push), dan hanya atas izin pemilik.

### Akun petugas

Pendaftaran tertutup (`ALLOW_REGISTRATION=false`). Sampai fitur undangan admin dibuat, akun
dibuat lewat perintah di server. Akun tamu "Coba contoh" dibuat server web lewat
`TAMU_RAHASIA` dan dihapus setelah 24 jam.

### Email

Reset sandi, undangan, peringatan spesies prioritas, dan notifikasi server memakai satu akun
Gmail dengan App Password. Kredensial disimpan pemilik di server (`/etc/gemahutan/notif.env`),
tidak pernah dikirim lewat chat atau dimasukkan ke git.

### Tugas terjadwal

| Cron | Isi |
|---|---|
| `/etc/cron.d/gemahutan-backup` | 02.30 WIB, `ops/backup_prod.sh`, terenkripsi age. Pulihkan: `ops/RESTORE_PROD.md` |
| `/etc/cron.d/gemahutan-disk` | tiap jam, `ops/peringatan_disk.py`, email kalau disk di atas 80% |
| pembersih tamu | `python -m app.bersihkan_tamu`, menghapus akun tamu di atas 24 jam |

Backup masih di disk yang sama (`/var/backups/gemahutan`) sampai kredensial B2/R2 diisi.
Uptime Kuma jalan di `127.0.0.1:3001` server, dibuka lewat SSH tunnel.

### Larangan

- Tidak menjalankan uji beban ke gemahutan.site.
- Tidak `docker system prune` di server.
- Tidak mengisi data demo di server.

## ML Dataset

Audio tidak masuk git. Untuk mereproduksi:
```bash
# Perlu Xeno-canto API key (lihat NEEDS_FROM_YOU.md)
cd ml/data && python download.py

# Atau gunakan dataset sintetis untuk demo:
cd ml/data && python generate_synthetic.py
```

## Training

```bash
cd ml
python data/extract_embeddings.py
python train.py --epochs 100
python evaluate.py
```

Resume setelah interrupt:
```bash
python train.py --epochs 100 --resume
```

## Troubleshooting

- Container crash loop: `docker compose logs <service> --tail=50`
- DB migration error: `docker compose exec api alembic downgrade -1` lalu `upgrade head`
- MinIO bucket missing: restart api, bucket dibuat otomatis
- Port 3000 conflict: web sudah di port 3001

## Verifikasi Setelah Deploy

```bash
curl -s localhost:8000/healthz | python -m json.tool
# services.model harus "up" kalau worker hidup dan artefak model ada
curl -s localhost:8000/api/v1/model/info | python -m json.tool
docker compose exec redis redis-cli get gemahutan:worker:heartbeat
docker compose exec db psql -U gemahutan -d gemahutan -c \
  "select r.id, r.status, count(d.id) filter (where d.id is not null) as detections
   from recordings r left join detections d on d.recording_id = r.id group by 1,2 order by 1;"
```

Kalau ada rekaman yang statusnya `pending` lebih dari dua menit, worker tidak
mengambil job. Cek `docker compose logs worker` dan pastikan heartbeat terisi.

## Pengerasan sebelum deploy

Aplikasi menolak dijalankan kalau `ENVIRONMENT=production` dan konfigurasi masih
berbahaya. Pemeriksaan ada di `apps/api/app/config.py` (`production_problems`) dan
dijalankan saat start di `apps/api/app/main.py`. Yang diperiksa: JWT_SECRET dan
SECRET_KEY masih nilai contoh, kredensial MinIO masih minioadmin, dan CORS masih
menyertakan localhost atau wildcard.

Kalau salah satu masih terpenuhi, container keluar dengan pesan:

    RuntimeError: Konfigurasi produksi belum aman, aplikasi sengaja tidak dijalankan:
    JWT_SECRET masih nilai contoh; ...

Bangkitkan rahasia sungguhan sebelum deploy:

    python3 -c "import secrets; print(secrets.token_urlsafe(48))"

Isi `JWT_SECRET` dan `SECRET_KEY` di `deploy/.env.prod`, dan ganti kredensial MinIO.
`ENVIRONMENT=production` juga mematikan `/docs`, `/redoc`, dan `/openapi.json`
secara otomatis supaya permukaan API tidak terbuka untuk umum. Kalau dokumentasi
memang diperlukan di server, set `ENABLE_DOCS=true`.

### Yang sudah dijamin aplikasi

| Perlindungan | Perilaku |
|---|---|
| Token dicabut saat logout | jti access dan refresh token dicatat di Redis sampai kedaluwarsa, jadi token lama tidak bisa dipakai lagi |
| Pembatas login | lima percobaan gagal per email dan alamat IP dalam satu menit, percobaan berikutnya dijawab 429 dengan Retry-After |
| Data lapangan | recordings, species, sites, stats, jobs, exports, dan me menolak akses tanpa token (401) |
| Pesan galat | detail teknis masuk log container, klien hanya menerima pesan umum |
| Berkas audio | diambil lewat API yang butuh token, bucket tidak dibuka publik |

### Yang belum ada

- Undangan akun oleh admin (sekarang akun dibuat lewat perintah di server).
- Kuota unggahan harian per akun petugas. Yang ada: pembatas 20 unggahan per menit per IP dan
  kuota 10 per 24 jam untuk akun tamu.
- Pemindaian berkas unggahan.
- Backup di luar server.

### Verifikasi cepat

    make security-check

Enam pemeriksaan dijalankan terhadap stack yang hidup: endpoint data menolak akses
tanpa token, logout mencabut token, login dikunci setelah percobaan gagal berulang,
port hanya terikat ke localhost, `.env` tidak memakai nilai contoh, dan tidak ada
kredensial yang ikut git. Kode keluar 1 kalau ada yang gagal.

