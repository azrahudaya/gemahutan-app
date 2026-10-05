> **Arsip, tidak berlaku lagi.** Dipindahkan ke `docs/arsip/` pada 3 Oktober 2026. Acuan yang
> berlaku: `docs/VISI_DAN_RUANG_LINGKUP.md`. Isi di bawah boleh dibaca untuk sejarah, tetapi
> jangan dijadikan dasar tugas.

# Arsitektur Lengkap GemaHutan

Disusun 23 September 2026. Keputusan teknis konsisten dari hulu ke
hilir. Satu sumber kebenaran. Setiap pilihan algoritma punya
alasan, setiap modul punya tanggung jawab jelas.

## 1. Visi produk

GemaHutan adalah platform bioakustik untuk hutan tropis Indonesia.
Tiga prinsip (sumber: `docs/proposal/proposal.md`):

1. Kejujuran ilmiah: confidence = skor model, threshold per spesies,
   status verifikasi eksplisit.
2. Human-in-the-loop: ahli memverifikasi, hasilnya jadi bahan latih.
3. Low-cost first: jalan di HP Android dan AudioMoth tanpa GPU.

## 2. Bentuk produk

Tiga lapisan (sumber: `docs/RENCANA_PRODUK.md`):

- **Web (Next.js)**: control plane untuk ranger, peneliti, admin.
  Dasbor, peta, verifikasi, ekspor.
- **Android (Kotlin)**: alat tangkap lapangan. Rekam fg + bg,
  antrean lokal, resume upload.
- **Edge agent (Python, direncanakan)**: daemon untuk AudioMoth
  dan Raspberry Pi. Capture + antrian, tidak inference.

Inference tetap di server. Tidak ada edge inference sampai ada
benchmark hardware.

## 3. Stack teknologi

| Layer | Pilih | Alasan |
|---|---|---|
| Frontend | Next.js 15 App Router + TS | Server Components kurangi JS, ekosistem luas |
| Styling | Tailwind 3 + CSS vars hex | Token-driven, no hsl(var()) antipattern |
| Komponen | shadcn/ui + Lucide | Copy-paste source, bukan library besar |
| State | TanStack Query + nuqs | Cache + invalidation, query string untuk filter |
| Audio | WaveSurfer.js | Render waveform + spektrogram dari PCM |
| Peta | MapLibre GL + OSM raster | Tanpa API key, atribusi jelas |
| Realtime | EventSource (SSE) | Token via query, fallback polling 5 detik |
| Form | react-hook-form + zod | Validasi typed, error inline |
| API | FastAPI + Pydantic v2 | Async native, OpenAPI otomatis |
| ORM | SQLAlchemy 2.0 async + Alembic | Migrasi versioned, raw SQL escape hatch |
| DB | PostgreSQL 16 + PostGIS 3.4 | Geometri native, JSON, indeks kuat |
| Queue | Redis 7 + ARQ | Async, idempotent, cron built-in |
| Storage | MinIO (S3 API) | Presigned URL, lokal dev, AWS-ready |
| Worker image | Python 3.11 + numpy + librosa + birdnetlib | Ringan, tanpa PyTorch |
| ML Track A | BirdNET-Analyzer v2.4 | Zero-shot 6522 spesies, facto standard |
| ML Track B | BirdNET embedding 1024-d + MLP numpy | Frozen backbone, latih ringan |
| Indeks | scikit-maad | ACI/NDSI/ADI/BI, ekosistem riset |
| Android | Kotlin + Compose Material3 | minSdk 26, targetSdk 34 |
| Android audio | MediaRecorder AAC dalam MPEG-4 | Standar, semua peramban/HP dukung |
| Android queue | Room SQLite | Checkpoint + retry native |
| Android sync | WorkManager + Retrofit + OkHttp | Resume upload, hemat baterai |
| Deploy | Docker Compose + Caddy | HTTPS otomatis via Let's Encrypt |
| CI | GitHub Actions | Test + build image + push ke GHCR |

## 4. Model ML

### Algoritma deteksi

Tiga tahap berurutan (Cascade Engine, sumber: `ml/engines/cascade.py`):

1. **BirdNET-Analyzer v2.4 zero-shot** (Track A). Audio disegment
   3 detik, BirdNET memberi daftar kandidat dengan confidence dan
   posisi temporal. Dipakai sebagai penjaring dengan cakupan global
   (6522 spesies).
2. **Embedding classifier MLP 2-lapis** (Track B). Dari audio yang
   sama, BirdNET menghasilkan vektor embedding 1024-d (GLOBAL_AVG_POOL
   dari layer sebelum klasifikasi). MLP dengan hidden 256, output
   26 kelas (25 spesies Indonesia + 1 negatif). Embedding backbone
   dibekukan, hanya MLP yang dilatih.
3. **Merge + threshold per spesies**: Track B menimpa skor BirdNET
   untuk 25 spesies Indonesia karena lebih akurat untuk spesies
   lokal. Spesies lain pakai skor BirdNET. Threshold kalibrasi per
   spesies dari validation set.

### Justifikasi algoritma

- **BirdNET bukan Random Forest / CNN sendiri**. BirdNET dilatih
  dengan 1 juta rekaman dari Xeno-canto + Macaulay + lain, akurasi
  publikasi 0,79 pada data global. Membangun sendiri berarti butuh
  dataset 100x lebih besar. Bukan pilihan realistis untuk 4 minggu.
- **Embedding + MLP bukan fine-tune full**. Fine-tune unfreeze
  backbone butuh GPU dan rentan overfit pada 1370 klip. Embedding
  frozen + MLP numpy (256 hidden, lr 0,001, epoch 300, seed 42)
  terbukti memberi 0,7156 uji bersih dengan biaya latih < 10 menit
  di CPU.
- **Numpy bukan PyTorch**. PyTorch menambah 800 MB image. MLP 2
  lapis cukup dengan numpy dan backprop manual (sudah ada di
  `ml/train.py:23-48`). Trade-off: model tidak bisa di-export ke
  ONNX, tapi worker tidak butuh itu.

### Kalibrasi threshold

Ambang hasil kalibrasi disimpan di `ml/reports/thresholds.json`.
Nilai beda per spesies: Gallus gallus 0,20, Prinia familiaris 0,60,
Chalcophaps indica 0,20, dst. `_negative` 0,15.

Alasan beda: model jauh lebih yakin pada spesies yang sering muncul
di data latih. Ambang seragam akan menurunkan F1 untuk spesies
langka atau yang mirip suara lain.

### Confidence calibration

Sekarang `confidence` adalah skor mentah softmax, bukan probabilitas
terkalibrasi. Untuk lomba, kita klaim "skor model", bukan
"peluang benar". Jika juri mempertanyakan, tambahkan temperature
scaling:

```
T = argmin_T NLL(softmax(logit / T), y_val)
```

Pakai validation set 193 klip. Update `ml/engines/embedding_clf.py`
agar confidence = softmax(logit / T). T ekspektasi antara 1,0 dan
2,0. Tidak wajib, hanya kalau ditanya.

### Algoritma lokalisasi

**GCC-PHAT** (sumber: `ml/localization.py`):

- Tiap pasangan mikrofon dihitung TDOA dengan generalized
  cross-correlation phase transform. PHAT menajamkan puncak pada
  suara bernada seperti kicauan burung.
- Resolusi lag di bawah satu sampel lewat interpolasi parabola 3
  titik puncak.
- Untuk azimuth, semua sudut 0-360 dicoba dengan langkah 0,5
  derajat, hitung RMS galat TDOA terukur vs teoritis, pilih minimum.
- Array mikrofon segaris punya kelemahan: sudut cermin menghasilkan
  TDOA identik (efek garis). Solusi: pisahkan sebagai
  `arah_kembar` (bukan keraguan).

**Jarak** (`jarak_dari_selisih_level`):

- Hukum fisika: level sumber berbanding terbalik dengan jarak (1/r).
- Input: level RMS jendela deteksi (dBFS), level referensi
  (dBFS), jarak referensi (m).
- Rumus: `jarak = jarak_ref * 10 ** ((level_ref - level_ukur) / 20)`.
- Sangat sensitif: salah taksir level sumber 6 dB = jarak 2x lipat.
  Karena itu `range_m` null ketika belum dikalibrasi.

**Triangulasi** (untuk >= 2 perangkat dengan jam sync):

- Buat grid 200x200 m dengan langkah 2 m.
- Akumulasi galat sudut dari tiap perangkat.
- Pilih titik dengan total galat minimum.
- Belum dipakai end-to-end karena belum ada data multi-perangkat.

### Spektrogram dan indeks

- **Spektrogram** (`scipy.signal.spectrogram` + matplotlib magma
  colormap): PNG cache di MinIO. Worker pre-render setelah deteksi.
- **Acoustic indices** (`scikit-maad`):
  - ACI (Acoustic Complexity Index): variasi energi dalam pita
    frekuensi.
  - NDSI (Normalized Difference Soundscape Index): rasio
    bioacoustic/antropogenic.
  - ADI (Acoustic Diversity Index): distribusi energi antar pita.
  - BI (Bioacoustics Index): area di bawah kurva 2-11 kHz.

## 5. Backend API

### Endpoint (36 path, sudah ada)

Lengkap di `docs/API.md` dan `openapi.json`. Yang penting:

- Auth: register/login/refresh/logout/me
- Recordings: CRUD + upload + batch + detections + audio + spectrogram + indices
- Batches: list + detail
- Jobs: list + stream (SSE) + retry
- Sites/devices/users: CRUD (admin only untuk tulis)
- Species: list + detail + detections per spesies
- Stats: overview, species, timeline
- Exports: verified, recordings (CSV/JSON)
- Model info, healthz, readyz

### Authorization model

Keputusan produk: **single-tenant**. Satu kawasan konservasi, satu
instansi. Semua ranger melihat semua rekaman, semua lokasi, semua
perangkat. Filter ownership hanya untuk admin operation (audit log).

Konsekuensi:
- `/api/v1/jobs`, `/batches`, `/stats`, `/exports` return 200 untuk
  ranger karena tidak ada filter tenant. Ini by design, bukan bug.
- Lokasi spesies terancam (pengaburan koordinat) bukan kebutuhan
  saat ini. Dokumentasikan di `docs/DECISIONS.md` jika将来需.

### Audit log

Tambah tabel `audit_log`:
- id, user_id, action (role_change, verify, delete, retry,
  settings_change), target_type, target_id, before_json,
  after_json, ip, created_at.

Endpoint `GET /api/v1/audit` (admin only) dengan filter
user_id, action, rentang tanggal.

## 6. Database schema

8 tabel (sumber: `apps/api/app/models/tables.py`):

- **users**: id, email, password_hash (Argon2), name, role
  (ranger/researcher/admin), is_active, last_login.
- **sites**: id, name, geom POINT srid 4326, habitat_type,
  elevation_m, description, owner_id, created_at.
- **devices**: id, name, type (audiomoth/phone/other), site_id,
  serial, channel_count, mic_spacing_m, reference_distance_m,
  reference_level_db, installed_at, active, notes.
- **recordings**: id, site_id, device_id, uploaded_by,
  storage_key, original_filename, duration_s, sample_rate,
  channels, recorded_at, status, error_message, batch_id.
- **species**: id, scientific_name, common_name, family,
  default_threshold, model_supported, iucn_status.
- **detections**: id, recording_id, species_id, start_time_s,
  end_time_s, confidence, source (birdnet/embedding),
  azimuth_deg, azimuth_confidence, azimuth_kembar_deg, range_m,
  localization_engine, verified_status, verified_by, verified_at.
- **acoustic_indices**: id, recording_id, aci, ndsi, adi, bi.
- **jobs**: id, recording_id, status, attempts, last_error,
  started_at, finished_at, progress, stage.

Tambahan (akan ditambah):
- **audit_log**: seperti di atas.
- **batches**: dipisah dari recording.batch_id untuk query cepat.

Index: site_id, device_id, species_id, status, recorded_at,
uploaded_by.

## 7. Worker reliability

### Bug yang harus diperbaiki

1. **FK acoustic_indices**: bungkus `session.add(recording);
   session.flush(); session.add(acoustic_indices); session.commit()`
   dalam try/except IntegrityError + rollback.
2. **noverlap >= nperseg**: tambahkan `noverlap = min(nperseg // 2,
   max(1, nperseg - 1))` di pemanggilan `sound.spectrogram`.
3. **Webm corrupt minimum**: tolak webm < 1 KB di validator ffprobe.

### Heartbeat

Worker tulis ke Redis key `gemahutan:worker:heartbeat` tiap 5 detik.
API baca untuk `/healthz` dan `/readyz`. Kalau heartbeat > 30 detik,
worker dianggap mati. Watchdog restart container.

### Retry policy

- Maks 3 attempt per job.
- Setelah 3 gagal, status `failed` permanen sampai di-retry manual
  lewat `POST /api/v1/jobs/{id}/retry`.
- Backoff exponensial: 10 detik, 30 detik, 90 detik.

## 8. Frontend (Next.js)

### Arsitektur folder

```
apps/web/src/
  app/
    (public)/
      page.tsx              # landing
      masuk/page.tsx
      daftar/page.tsx
    (app)/
      layout.tsx            # AppShell dengan sidebar
      dashboard/page.tsx
      rekaman/page.tsx
      rekaman/[id]/page.tsx
      rekaman/baru/page.tsx
      rekam/page.tsx
      lokasi/page.tsx
      lokasi/[id]/page.tsx
      lokasi/baru/page.tsx
      perangkat/page.tsx
      perangkat/[id]/page.tsx
      spesies/page.tsx
      spesies/[id]/page.tsx
      laporan/page.tsx
      model/page.tsx
      admin/akun/page.tsx
      dokumentasi/page.tsx
    api/                   # BFF tipis kalau perlu
    globals.css            # token CSS hex
  components/
    app-shell.tsx
    sidebar.tsx
    top-bar.tsx
    data-table.tsx
    filter-bar.tsx
    empty-state.tsx
    error-state.tsx
    loading-skeleton.tsx
    stat-card.tsx
    audio-player.tsx
    spectrogram-viewer.tsx
    map-lokasi.tsx
    form-field.tsx
    dialog-konfirmasi.tsx
  lib/
    api.ts                 # fetch wrapper, auto-refresh token
    auth.tsx               # context + hook
    format.ts              # format tanggal, keyakinan, durasi
    query-client.ts
    use-job-stream.ts      # SSE hook + polling fallback
  hooks/
    use-recordings.ts
    use-recording.ts
    use-species.ts
    use-stats.ts
  test/
    format.test.ts
    api.test.ts
    auth.test.tsx
```

### Server vs Client Component

Default Server Component. Client Component hanya untuk:
- Interactive form (react-hook-form)
- Audio player (WaveSurfer butuh DOM)
- Peta MapLibre (canvas)
- Tombol dengan onClick
- EventSource untuk SSE

### State management

- TanStack Query untuk data server (cache 30 detik, stale 60
  detik, refetch on focus).
- nuqs untuk filter di URL (shareable).
- Context untuk auth + theme.
- Local state untuk UI (useState).

### Error handling

Setiap fetch dibungkus try/catch. Server error tampilkan
`ErrorState` dengan tombol coba lagi. Network error tampilkan
"Notifikasi: Anda offline, cek koneksi".

### Accessibility

- Setiap input punya label htmlFor + id.
- Fokus keyboard terlihat (ring 2px #4C7DFF di luar elemen).
- Modal: tutup Escape, fokus kembali ke pembuka, `inert` saat
  tertutup.
- Tap target minimum 44x44 px.
- Skip to main content link.
- `aria-live="polite"` untuk SSE update.

## 9. Android

### Modul

- **capture**: Service foreground `type=microphone` yang merekam
  AAC dalam MPEG-4 (.m4a) 48 kHz mono 96 kbps.
- **queue**: Room SQLite, tabel `recording_local` dengan status
  (captured, uploading, uploaded, failed).
- **sync**: WorkManager + Retrofit + OkHttp. Upload dengan
  `Content-Length` + `Content-MD5` agar server bisa validasi
 完整性. Resume dari byte terakhir kalau gagal di tengah.
- **ui**: Compose Material3 dark. Minimal: pilih lokasi + mulai
  rekam + lihat antrian.

### Token management

Token JWT disimpan di `EncryptedSharedPreferences` (AES256 GCM).
Refresh token dipakai untuk perpanjang access token 5 menit sebelum
expired.

### Perizinan runtime

Android 13+: `RECORD_AUDIO`, `ACCESS_FINE_LOCATION`,
`POST_NOTIFICATIONS` runtime request.
Android 14+: tambah `FOREGROUND_SERVICE_MICROPHONE` di manifest.

## 10. Package Python

### Struktur

```
pyproject.toml
gemahutan/
  __init__.py
  ml/
    __init__.py
    train.py
    evaluate.py
    field_eval.py
    degradation.py
    localization.py
    engines/
      base.py
      birdnet.py
      embedding_clf.py
      cascade.py
  cli/
    train.py
    evaluate.py
    degrade.py
```

### Entry point

```toml
[project.scripts]
gemahutan-train = "gemahutan.cli.train:main"
gemahutan-eval = "gemahutan.cli.evaluate:main"
gemahutan-degrade = "gemahutan.cli.degrade:main"
```

### Dependensi

- numpy, librosa, scipy, soundfile
- scikit-maad, birdnetlib, resampy
- pydantic (untuk config)

Build wheel: `python -m build`. Publish ke TestPyPI dulu, validasi,
baru PyPI.

## 11. Deployment

### Single-server Compose

```yaml
# docker-compose.yml
services:
  db:        # postgis/postgis:16-3.4
  redis:     # redis:7-alpine
  minio:     # quay.io/minio/minio
  api:       # build apps/api
  worker:    # build apps/worker
  web:       # build apps/web
  caddy:     # caddy:2-alpine + Caddyfile
```

Caddy reverse proxy ke api dan web di localhost. Port 80 dan 443
expose. Domain publik + Let's Encrypt otomatis.

### Production hardening

- `ENVIRONMENT=production` menolak startup kalau JWT_SECRET,
  SECRET_KEY, kredensial MinIO masih nilai contoh, atau CORS masih
  localhost.
- `ALLOW_REGISTRATION=false`.
- Password admin di-rotate via CLI setelah deploy.
- HTTPS only, HSTS 1 tahun, CSP `default-src 'self'`.
- Backup harian DB + MinIO ke object storage offsite.

### Backup policy

```bash
# ops/backup.sh
pg_dump gemahutan | gzip | aws s3 cp - s3://backup/db/$(date +%F).sql.gz
mc mirror minio/gemahutan-audio s3://backup/audio/
```

Restore diuji tiap bulan, bukan hanya dibuat.

## 12. Lisensi data

Manifest harus bersih dari ND sebelum training apa pun:

```
filter: license NOT LIKE '%nd%'
```

Pipeline: `prepare.py` -> `extract_embeddings.py` -> `train.py`.
Setiap langkah baca manifest yang sudah disaring. Simpan hash
SHA-256 manifest di `ml/data/manifest.sha256` untuk audit.

## 13. Yang TIDAK dibangun

- Multi-tenant. Bukan kebutuhan lomba.
- Streaming inference (WebSocket). SSE + polling cukup.
- Edge inference (Raspberry Pi). Capture dulu, inference menyusul.
- Flutter. Native Kotlin sudah cukup untuk Android-only.
- Mobile app iOS. Target USB 2026 tidak butuh.
- Export PDF dari server. Browser print cukup untuk laporan.
- Real-time collaboration (multi-user edit). Tidak perlu.

## 14. Ukuran keberhasilan

Lomba USB 2026 dinilaikan 100 poin:
- Inovasi 20
- Dampak 20
- UI/UX 20
- Metodologi 20
- Kesesuaian 10
- Urgensi 10

Plus presentasi 50 + tantangan juri 50.

Fokus:
- Inovasi: cascade BirdNET + embedding + threshold per spesies
  + verifikasi loop + arah datang. Ceritakan ini.
- Dampak: enumerate use case nyata (Taman Nasional, hutan kota,
  monitoring populasi).
- UI/UX: tunjukkan dashboard dengan data riil dari 242 klip
  lapangan.
- Metodologi: 8 tingkat degradasi terukur, kalibrasi threshold,
  precision-recall per spesies.

## 15. Eksekusi

Semua keputusan di atas sudah dikunci. Yang tersisa hanya
mengerjakan, bukan merancang ulang.

Urutan dimulai dari `docs/RENCANA_30_HARI.md`, tapi setiap tugas
bisa dilakukan paralel kalau tidak konflik di file yang sama.
