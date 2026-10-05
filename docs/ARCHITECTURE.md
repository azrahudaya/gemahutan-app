# Arsitektur GemaHutan

Keadaan per 3 Oktober 2026. Untuk apa yang dibangun dan apa yang tidak, lihat
`docs/VISI_DAN_RUANG_LINGKUP.md`. Dokumen ini hanya menjelaskan bagaimana sistemnya tersusun.

## Alur data

```
[Alat perekam / peramban HP] --> [Unggah] --> [MinIO]
                                                 |
                                          [Redis + ARQ]
                                                 |
                                            [Worker]
                                   BirdNET + classifier lokal (cascade)
                                   indeks soundscape, spektrogram
                                                 |
                                     [PostgreSQL 16 + PostGIS]
                                                 |
                                         [FastAPI /api/v1]
                                                 |
                                   [Next.js] di belakang [Caddy HTTPS]
```

## Komponen

| Bagian | Isi |
|---|---|
| `apps/web` | Next.js 15 (App Router, output standalone), React 19, Tailwind 4 + daisyUI 5 tema `gemahutan`, TanStack Query, MapLibre GL, WaveSurfer.js, Recharts, Remotion (video halaman depan) |
| `apps/api` | FastAPI, Pydantic v2, SQLAlchemy 2 async + Alembic, JWT access + refresh, Argon2 |
| `apps/worker` | ARQ. Menjalankan inferensi, indeks soundscape (scikit-maad: ACI, NDSI, ADI, BI), pre-render spektrogram |
| `ml/` | Pelatihan, evaluasi, checkpoint, `ml/localization.py` |
| `deploy/` | Compose produksi, Caddyfile, filter rsync |
| `ops/` | Deploy, sinkron repo publik, backup, peringatan disk, audit |

## Model

- **Cascade**: BirdNET-Analyzer menghasilkan embedding dan skor, lalu classifier lokal
  (regresi logistik di atas embedding) memilih di antara 25 spesies burung Indonesia.
- Ambang per spesies, dikalibrasi. Skor yang tampil adalah skor model, bukan probabilitas pasti.
- Mesin dipilih lewat `INFERENCE_ENGINE` (`cascade` di produksi). Worker butuh
  `ml/embeddings/label_map.json` dan checkpoint aktif, kalau tidak ia jatuh ke BirdNET saja.
- Checkpoint produksi saat ini v3. v5 (lisensi data bersih) menunggu promosi.

## Lokalisasi (dasar simulasi dan Tahap 3)

Fungsi sudah ada di `ml/localization.py`, belum tersambung ke aplikasi:

- `gcc_phat`, `tdoa_pasangan`, `estimasi_arah`: arah datang suara dari satu alat
  multi-mikrofon. Larik mikrofon segaris punya sudut cermin, ditandai sebagai arah kembar.
- `jarak_dari_selisih_level`: jarak dari selisih level suara (hukum 1/r). Sangat peka:
  salah 6 dB berarti jarak dua kali lipat, jadi jarak hanya diisi setelah alat dikalibrasi.
- `triangulasi`: area perkiraan dari arah beberapa alat yang jamnya tersinkron (grid,
  galat minimum).
- `bangun_sintetis`: membuat sinyal buatan untuk menguji fungsi di atas. Fitur simulasi
  perkiraan lokasi di Tahap 1 memakai pendekatan ini dengan alat virtual.

## Hak akses

- Peran: `admin`, `researcher` (peneliti), `ranger`.
- `require_verifier` (peneliti, admin) untuk verifikasi. `require_admin` untuk lokasi,
  perangkat, pengguna, audit, percobaan ulang job.
- Akun tamu halaman depan (`*@tamu.gemahutan.invalid`) dibatasi daftar izin di
  `apps/api/app/services/tamu.py`.
- Ranger hanya membaca rekamannya sendiri dan data turunannya lewat `recording_scope` di
  `apps/api/app/services/access.py`. Rekaman orang lain dijawab 404.
- Target aturan per peran ada di `docs/VISI_DAN_RUANG_LINGKUP.md` bagian 4.

## Produksi

- Satu VPS, `deploy/docker-compose.prod.yml` dengan profil `pekerja` untuk worker.
- Layanan: db (postgis 16-3.4), redis 7, minio (`ghcr.io/azrahudaya/minio:2025-gemahutan`),
  api, worker, web, caddy 2.
- Satu kawasan per server. Data multi-kawasan baru di Tahap 5.
- Cara deploy: `docs/DEPLOY.md`.
