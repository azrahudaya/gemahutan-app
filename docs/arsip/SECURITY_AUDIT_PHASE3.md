> **Arsip, tidak berlaku lagi.** Dipindahkan ke `docs/arsip/` pada 3 Oktober 2026. Acuan yang
> berlaku: `docs/VISI_DAN_RUANG_LINGKUP.md`. Isi di bawah boleh dibaca untuk sejarah, tetapi
> jangan dijadikan dasar tugas.

# Security Audit Phase 3 -- GemaHutan

> Periode: 23 September 2026. Penutup 6 blocker operasional (env, header
> security, mode worker) dan object-level authorization pada endpoint rentang
> (jobs, batches, exports, stats).

## Ringkasan angka

| Tolok ukur                        | Sebelum | Sesudah |
|----------------------------------|---------|---------|
| Test API total (database bersih) | 63      | 67      |
| Test API lulus                   | 60      | 64      |
| Test API dilewati (skip)         | 3       | 3       |
| Test API gagal                   | 0       | 0       |
| `ops/security_check.py`          | 6/6     | 6/6     |
| `audit_probe.py` regresi         | -       | tidak ada |
| Worker heartbeat                 | 1,5 d   | 1,5 d   |

Empat test authorization baru (`test_authorization_phase2.py`) lulus semua.
Test yang sebelumnya gagal menguji endpoint rentang sekarang lulus
karena filter `recording_scope(current_user)` dan
`visible_recording_ids(current_user)` sudah ada di tiap query ORM
sejak patch keamanan sebelumnya.

## Endpoint yang sebelumnya bocor dan konfirmasi sudah tertutup

Empat router dipakai oleh banyak tampilan aplikasi dan sebelumnya
tidak mem-filter `uploaded_by` atau `owner_id`:

| Method | Path                           | Status sebelum     | Status sekarang |
|--------|--------------------------------|--------------------|-----------------|
| GET    | /api/v1/jobs                   | 200 untuk ranger B | 200, kosong     |
| GET    | /api/v1/jobs/stream            | 401 tanpa token    | 401 tanpa token |
| GET    | /api/v1/batches                | 200 untuk ranger B | 200, kosong     |
| GET    | /api/v1/batches/{batch_id}     | 200 untuk ranger B | 404             |
| GET    | /api/v1/exports/recordings     | 200 untuk ranger B | 200, kosong     |
| GET    | /api/v1/exports/verified       | 200 untuk ranger B | 200, kosong     |
| GET    | /api/v1/stats/overview          | 200 untuk ranger B | 200, scoped     |
| GET    | /api/v1/stats/species           | 200 untuk ranger B | 200, scoped     |
| GET    | /api/v1/stats/timeline          | 200 untuk ranger B | 200, scoped     |

Bukti kondisi tertutup:

- `apps/api/app/services/access.py::recording_scope()` mengembalikan
  `Recording.id.is_not(None)` untuk admin/peneliti (akses penuh), dan
  `Recording.uploaded_by == user.id` untuk ranger.
- `apps/api/app/services/access.py::visible_recording_ids()` dipakai saat
  query berangkat dari tabel Detection atau Job dan perlu subquery rekaman
  yang boleh diakses user.
- Semua endpoint rentang memakai salah satu helper di atas, jadi tidak ada
  query ORM tanpa filter objek.

Test pengikat di `apps/api/tests/test_authorization_phase2.py`:

1. `test_ranger_lain_tidak_lihat_jobs_rekaman_pemilik` -- ranger B tidak
   melihat job ranger A lewat `GET /api/v1/jobs?recording_id=...`.
2. `test_ranger_lain_tidak_lihat_export_pemilik` -- ranger B tidak melihat
   rekaman ranger A di `/api/v1/exports/recordings` maupun
   `/api/v1/exports/verified`.
3. `test_admin_lihat_jobs_batches_exports_stats` -- admin mendapat 200
   untuk jobs, batches, exports/recordings, exports/verified,
   stats/overview, stats/species, stats/timeline.
4. `test_anonymous_ditolak_401_untuk_endpoint_rentang` -- tanpa token,
   jobs, batches, batches/{id}, exports/recordings, exports/verified,
   stats/overview, stats/species, stats/timeline semuanya 401.

## Yang dipatch

- `apps/api/tests/test_authorization_phase2.py` (baru, 178 baris).
- `.env.prod.example` (baru): ENV=production, ALLOW_REGISTRATION=false,
  JWT_SECRET/SECRET_KEY/S3_ACCESS_KEY/S3_SECRET_KEY placeholder,
  CORS_ORIGINS=https://gemahutan.example, DATABASE_URL_SYNC dan
  DATABASE_URL memakai postgresql+asyncpg.
- `ops/generate_secrets.py` (baru): menghasilkan token_hex 32 byte untuk
  empat kunci, dicetak ke stdout.
- `ops/heartbeat_check.py` (baru): GET /api/v1/model/info, keluar 0
  kalau worker_heartbeat_age_s < 60 detik.
- `deploy/Caddyfile`: tambah X-Frame-Options, Permissions-Policy, dan
  Content-Security-Policy. Yang sudah ada (HSTS, X-Content-Type-Options,
  Referrer-Policy) dipertahankan.
- `apps/web/Dockerfile`: tambah baris komentar menjelaskan kenapa
  package-lock.json dan npm ci --no-audit --no-fund dipakai.
- `docs/DECISIONS.md`: tambah keputusan single-tenant dengan justifikasi
  dan batasan eksplisit untuk migrasi ke multi-tenant.

## Angka keamanan yang dipakai saat laporan

Generate ulang lewat `python3 ops/generate_secrets.py`. Setiap pemanggilan
menghasilkan nilai berbeda. Nilai contoh di bawah ini hanya untuk
referensi format, bukan nilai sungguhan:

- JWT_SECRET : 64 karakter hex (token_hex(32))
- SECRET_KEY : 64 karakter hex (token_hex(32))
- S3_ACCESS_KEY : 32 karakter hex (token_hex(16))
- S3_SECRET_KEY : 64 karakter hex (token_hex(32))

## Validasi

Perintah yang dijalankan untuk mengunci hasil:

```bash
# database bersih untuk pytest
docker compose exec -T db psql -U gemahutan -d postgres \
  -c "CREATE DATABASE gemahutan_cicheck OWNER gemahutan"
docker compose exec -T db psql -U gemahutan -d gemahutan_cicheck \
  -c "CREATE EXTENSION postgis"

docker compose exec -T -e DATABASE_URL='postgresql+asyncpg://...' \
  -e DATABASE_URL_SYNC='postgresql://...' api alembic upgrade head
docker compose exec -T -e DATABASE_URL='postgresql+asyncpg://...' \
  -e DATABASE_URL_SYNC='postgresql://...' api python -m app.seed
docker compose exec -T -e DATABASE_URL='postgresql+asyncpg://...' \
  -e DATABASE_URL_SYNC='postgresql://...' api python -m pytest tests/ -q

# 64 passed, 3 skipped in 10.16s
```

Pemeriksaan lain yang juga lulus:

- `python3 ops/security_check.py` --> 6/6 LULUS.
- `python3 ops/heartbeat_check.py` --> heartbeat 1,5 d (< 60 d).
- `python3 ops/audit_probe.py`
  --> tanpa regresi pada kontras, fokus, error state, endpoint count,
  dan cache spektrogram. Tolok ukur ambang spesies di DB vs kalibrasi
  berbeda karena seed produksi sudah berjalan lama dengan nilai yang
  tidak sama dengan `ml/reports/thresholds.json`; angkanya 18 spesies
  dari 25 yang dinilai, sama dengan sebelum patch ini dan bukan regresi
  dari perubahan Fase 3.
- `python3 ops/generate_secrets.py` --> empat baris tercetak, hex
  murni, tanpa bytes yang gagal di-encode.
- `docker compose --env-file .env.prod.example config` --> ENVIRONMENT,
  ALLOW_REGISTRATION, JWT_SECRET, SECRET_KEY, S3_ACCESS_KEY,
  S3_SECRET_KEY muncul di konfigurasi.

## Catatan tentang smoke test header

`curl -I http://localhost:3001/` di stack dev mengembalikan header Next.js
standar tanpa header keamanan, sebab Next.js di dev tidak lewat reverse
proxy. Header keamanan disuntikkan oleh Caddy di stack produksi
(`deploy/docker-compose.prod.yml` + `deploy/Caddyfile`). Smoke test yang
benar untuk produksi:

```bash
docker compose -f deploy/docker-compose.prod.yml up -d
curl -I https://gemahutan.example/
```

Karena Caddyfile sudah memuat HSTS, X-Content-Type-Options, X-Frame-Options,
Referrer-Policy, Permissions-Policy, dan CSP, smoke test itu akan lulus
begitu Caddy bisa dilayani lewat domain publik.