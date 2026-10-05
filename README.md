# GemaHutan

[![CI](https://github.com/azrahudaya/gemahutan/actions/workflows/ci.yml/badge.svg)](https://github.com/azrahudaya/gemahutan/actions)
[![Python](https://img.shields.io/badge/python-3.11-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/fastapi-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/next.js-15-000000?logo=nextdotjs&logoColor=white)](https://nextjs.org)
[![PostgreSQL](https://img.shields.io/badge/postgresql-16-4169E1?logo=postgresql&logoColor=white)](https://postgresql.org)
[![PostGIS](https://img.shields.io/badge/postgis-3.4-4169E1)](https://postgis.net)
[![Redis](https://img.shields.io/badge/redis-7-DC382D?logo=redis&logoColor=white)](https://redis.io)
[![Docker](https://img.shields.io/badge/docker-compose-2496ED?logo=docker&logoColor=white)](https://docs.docker.com/compose)
[![BirdNET](https://img.shields.io/badge/birdnet-2.4-228B22)](https://github.com/kahst/BirdNET-Analyzer)
[![scikit-maad](https://img.shields.io/badge/scikit--maad-1.5-2E8B57)](https://scikit-maad.github.io)
[![TypeScript](https://img.shields.io/badge/typescript-5-3178C6?logo=typescript&logoColor=white)](https://typescriptlang.org)
[![Tailwind](https://img.shields.io/badge/tailwind-4-06B6D4?logo=tailwindcss&logoColor=white)](https://tailwindcss.com)
[![daisyUI](https://img.shields.io/badge/daisyui-5-1AD1A5)](https://daisyui.com)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

![GemaHutan](docs/assets/banner.png)

Platform passive acoustic monitoring untuk biodiversitas hutan tropis Indonesia. Rekam suara hutan, sistem mengenali 25 spesies burung Indonesia lewat BirdNET + classifier lokal, menghitung indeks soundscape, lalu menampilkan hasilnya di dashboard, peta, dan spektrogram untuk verifikasi ahli.

**Coba langsung: [gemahutan.site](https://gemahutan.site)**. Halaman depan memungkinkan satu unggahan tanpa akun (pengunjung mendapat akun tamu terpisah, dibersihkan otomatis 24 jam). Aplikasi petugas (dashboard, peta, laporan, verifikasi) dibuka dengan login per peran: admin, peneliti, dan ranger.

## Jalankan lokal

```bash
git clone https://github.com/azrahudaya/gemahutan.git
cd gemahutan
cp .env.example .env
docker compose up -d   # buka http://localhost:3001
```

Semua service (API, worker, web, database, redis, object storage) langsung hidup.

## Alur kerja

Rekam atau unggah audio -> antrean Redis -> preprocess (resample 48 kHz mono, segmentasi 3 detik) -> inference (BirdNET zero-shot + classifier 25 spesies Indonesia) -> ambang per spesies -> indeks soundscape (ACI, NDSI, ADI, BI) -> dashboard (player, spektrogram, peta, chart) -> verifikasi ahli -> data balik jadi bahan latih.

## Stack

| Layer | Teknologi |
|-------|-----------|
| Frontend | Next.js 15, TypeScript, Tailwind CSS 4, daisyUI 5 |
| API | FastAPI, Python 3.11, Pydantic v2 |
| Queue + worker | Redis + ARQ (inference BirdNET, classifier lokal, indeks) |
| Database | PostgreSQL 16 + PostGIS |
| Storage | MinIO (S3-compatible) |
| ML baseline | BirdNET-Analyzer v2.4 (zero-shot, 6500+ spesies) |
| ML lokal | Classifier di atas embedding BirdNET, 25 spesies Indonesia |
| Indeks akustik | scikit-maad (ACI, NDSI, ADI, BI) |
| Container | Docker Compose |

## Model

- Track A (baseline): BirdNET-Analyzer v2.4 zero-shot, aktif untuk 6500+ spesies global.
- Track B (lokal): classifier di atas embedding BirdNET, terlatih untuk 25 spesies Indonesia, ambang per spesies hasil kalibrasi.
- F1 makro CV bersarang per perekam 0,729 (CI95 0,690 sampai 0,751). Uji independen 131 klip negara lain: akurasi 0,756. Angka resmi di `ml/reports/angka_resmi.json`.
- Angka akurasi global sengaja tidak ditampilkan karena menyesatkan pada data imbalanced. Evaluasi per spesies ada di `ml/reports/`.

## Dokumentasi

| Dokumen | Isi |
|---------|-----|
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | Arsitektur, data model, service |
| [API.md](docs/API.md) | Kontrak API lengkap |
| [MANUAL.md](docs/MANUAL.md) | Manual pemakaian |
| [DECISIONS.md](docs/DECISIONS.md) | Keputusan teknis + alasan |
| [DEPLOY.md](docs/DEPLOY.md) | Panduan deploy ke VPS |
| [VISI_DAN_RUANG_LINGKUP.md](docs/VISI_DAN_RUANG_LINGKUP.md) | Visi, pengguna, tahapan, acuan utama |
| [LICENSES.md](docs/LICENSES.md) | Lisensi pihak ketiga |

## Status dan batasan

- Audio evaluasi berasal dari Xeno-canto dan korpus turunan, bukan rekaman lapangan asli. Angka ditulis apa adanya di `ml/reports/`.
- Aplikasi Android dan CLI portable masih rencana.
- Rincian yang dibangun dan yang belum ada tercantum di `docs/VISI_DAN_RUANG_LINGKUP.md`.

## Tim

USB 2026 kategori Software Development, Universitas Gunadarma.

| Nama | NPM | Peran |
|------|-----|-------|
| Artya Epriliani | 10124205 | Ketua (Sistem Informasi) |
| Azra Hudaya | 50423244 | Anggota |

## Lisensi

MIT (kode). Lisensi pihak ketiga dicatat di [docs/LICENSES.md](docs/LICENSES.md). BirdNET-Analyzer memakai lisensi CC BY-NC-SA 4.0 (non-komersial); penggunaan dalam konteks lomba atau riset diperbolehkan dengan atribusi.
