> **Arsip, tidak berlaku lagi.** Dipindahkan ke `docs/arsip/` pada 3 Oktober 2026. Acuan yang
> berlaku: `docs/VISI_DAN_RUANG_LINGKUP.md`. Isi di bawah boleh dibaca untuk sejarah, tetapi
> jangan dijadikan dasar tugas.

# Kontrak Fase 2 (semua workstream patuh ke berkas ini)

Dokumen ini satu-satunya sumber kebenaran untuk pekerjaan paralel sesi ini.
Kalau kode dan dokumen ini berselisih, perbaiki kodenya, jangan diam-diam menyimpang.

## Skema database (hanya WS-A yang membuat migrasi)

Migrasi baru: `apps/api/alembic/versions/` revisi tunggal, `down_revision = "9c1d2e3f4a5b"`.

- `jobs`: tambah `progress` (Integer, not null, default 0), `stage` (String(50), null).
- `recordings`: tambah `batch_id` (String(64), null, index).
- `detections`: tambah `azimuth_deg` (Float, null), `azimuth_confidence` (Float, null),
  `range_m` (Float, null), `localization_engine` (String(50), null).
- `devices`: tambah `serial` (String(120), null), `channel_count` (Integer, not null, default 1),
  `mic_spacing_m` (Float, null), `reference_distance_m` (Float, null),
  `reference_level_db` (Float, null), `installed_at` (DateTime tz, null),
  `active` (Boolean, not null, default true), `notes` (Text, null).
- `species`: tambah `model_supported` (Boolean, not null, default false).

Aturan migrasi: `alembic upgrade head` harus hijau, dan `alembic downgrade -1` lalu
`upgrade head` juga hijau.

## Tahap dan progres job

`stage` salah satu dari: `antre`, `unduh`, `dekode`, `birdnet`, `klasifikasi`,
`lokalisasi`, `indeks`, `spektrogram`, `selesai`, `gagal`.
`progress` 0 sampai 100 dengan patokan: antre 0, unduh 10, dekode 20, birdnet mulai 30
naik sampai 60, klasifikasi 60 sampai 75, lokalisasi 80, indeks 88, spektrogram 96,
selesai 100, gagal tetap di angka terakhir.

Worker wajib menulis progres setelah setiap tahap, bukan hanya di akhir. Kalau satu
tahap gagal, `stage` jadi `gagal` dan `progress` tidak dikembalikan ke nol.

## Endpoint baru dan yang berubah

Semua endpoint tetap butuh token, kecuali yang memang publik (`/healthz`, `/readyz`,
`/api/v1/auth/*`). Tanpa token harus 401, termasuk `/api/v1/jobs/stream`.

Perangkat, tulis hanya admin, baca untuk semua peran yang login:

- `GET /api/v1/devices?site_id=&active=` hasil
  `[{id, name, type, site_id, site_name, serial, channel_count, mic_spacing_m,
  reference_distance_m, reference_level_db, installed_at, active, notes,
  recording_count}]`
- `POST /api/v1/devices` body
  `{name, type, site_id, serial?, channel_count?, mic_spacing_m?,
  reference_distance_m?, reference_level_db?, installed_at?, notes?}` hasil 201 objek sama
- `PATCH /api/v1/devices/{device_id}` body sebagian, hasil objek sama
- `DELETE /api/v1/devices/{device_id}` hasil 204, dan 409 kalau masih ada rekaman memakai
  perangkat itu, pesannya menyebut jumlah rekaman

Akun, semua hanya admin:

- `GET /api/v1/users` hasil
  `[{id, email, name, role, created_at, is_active, recording_count, site_count}]`
- `PATCH /api/v1/users/{user_id}/role` body `{role}` hasil objek sama. Menolak 409 kalau
  mengubah peran diri sendiri, dan menolak 409 kalau menurunkan admin terakhir.
- `DELETE /api/v1/users/{user_id}` hasil 204. Menolak 409 untuk diri sendiri, dan 409
  kalau pengguna masih punya rekaman atau lokasi, pesannya menyebut jumlahnya.

Unggah batch:

- `POST /api/v1/recordings/batch` multipart, field `files` (1 sampai 20 berkas),
  `site_id` (int), `device_id` (int opsional), `recorded_at` (ISO 8601 opsional). Hasil 201
  `{batch_id, count, items: [{filename, recording_id, status, error}]}`. Satu berkas gagal
  tidak membatalkan sisanya, kegagalannya dicatat di `error`.
- `GET /api/v1/batches` hasil
  `[{batch_id, created_at, total, done, failed, progress_percent}]`, urut terbaru dulu.
- `GET /api/v1/batches/{batch_id}` hasil
  `{batch_id, total, done, failed, pending, processing, progress_percent,
  recordings: [{id, filename, status, progress, stage}]}`. `progress_percent` = rata-rata
  progres job dibulatkan. 404 kalau batch tidak ada.

Progres pada rekaman:

- Respons `GET /api/v1/recordings` dan `GET /api/v1/recordings/{id}` menambah `progress`
  (int) dan `stage` (string atau null) dari job rekaman itu, plus `batch_id`.
- `GET /api/v1/jobs` menerima `status` (misalnya `active` untuk pending dan running) dan
  `limit`, dan setiap item menambah `progress` dan `stage`.

Lokalisasi pada deteksi:

- Respons deteksi menambah `azimuth_deg`, `azimuth_confidence`, `range_m`,
  `localization_engine`. Null kalau tidak tersedia, jangan diisi nol palsu.
- `GET /api/v1/model/info` menambah blok `localization`:
  `{butuh_kanal_minimal: 2, butuh_geometri: true, terpasang_di_worker: bool,
  disimpan_ke_deteksi: bool, batas: [kalimat batas yang sudah diukur]}`.

Siaran status (bukan pengganti polling, tapi pelengkap):

- `GET /api/v1/jobs/stream?token=<access_token>` memakai `text/event-stream`.
  Event `job`, data JSON `{recording_id, job_id, status, progress, stage}`.
  Kirim snapshot semua job aktif saat koneksi dibuka, lalu kirim ulang saat ada perubahan,
  dengan heartbeat komentar setiap 15 detik. Tutup sendiri setelah 10 menit. Tanpa token
  yang sah jawab 401. Token lewat query diizinkan khusus endpoint ini karena EventSource
  tidak bisa mengirim header, dan batas itu harus ditulis di dokumen.
- Klien wajib tetap punya fallback polling 5 detik kalau stream gagal.

Unggahan audio:

- `ALLOWED_TYPES` dan `ALLOWED_EXTENSIONS` di `apps/api/app/routers/recordings.py` harus
  sama-sama memuat `webm` (rekaman dari browser). Daftar MIME dan ekstensi wajib sinkron.

## Web

Klien di `apps/web/src/lib/api.ts` sudah memuat fungsi berikut, jangan diubah namanya:

`getDevices(params)`, `createDevice(data)`, `updateDevice(id, data)`, `deleteDevice(id)`,
`getUsers()`, `updateUserRole(id, role)`, `deleteUser(id)`,
`uploadRecordingBatch(formData, onProgress)`, `getBatches()`, `getBatch(id)`,
`jobStreamUrl()`, `getJobs(params)`.

Item navigasi sudah ditambah: Upload, Rekam, Perangkat, Pengguna, Dokumentasi, Laporan.
Jangan menyunting `apps/web/src/components/layout.tsx` atau `apps/web/src/lib/api.ts`
kecuali kamu pemiliknya (koordinator).

Pemilik halaman:

- WS-C: `/upload`, `/rekam`, `/devices`, `/admin/users`, `/recordings`, `/recordings/[id]`.
- WS-D: `/dokumentasi`, `/laporan`, `/sites`, `/sites/[id]`, `components/sites-map.tsx`.

Aturan UI yang tidak bisa dinegosiasi: kontras teks minimal 4,5:1, target sentuh minimal
44 piksel (kelas `min-h-11`), penanda fokus terlihat, `prefers-reduced-motion` dihormati,
dan setiap panggilan data punya state memuat, kosong, dan galat.
Kontrol yang pasti ditolak API (tombol peran untuk non-admin) tidak boleh ditampilkan.

## Cara kerja paralel yang aman

- Jangan ada yang `git commit` atau `git push`. Koordinator yang commit.
- Jangan jalankan `next build` (dua proses di folder yang sama merusak `.next`).
  Pakai `npx tsc --noEmit` dan `npx vitest run` saja.
- WS-A pemilik build image `api` dan migrasi. WS-B pemilik build image `worker`.
  WS-C dan WS-D tidak membangun image.
- Setelah membangun ulang, bangunkan ulang lewat
  `docker compose up -d --force-recreate <service>`.

## Bukti yang wajib dilaporkan

Angka nyata, bukan klaim: keluaran pytest dengan jumlah lulus dan gagal, keluaran ruff,
kode HTTP dari `curl`, keluaran `npx tsc --noEmit`, jumlah test vitest, dan potongan
respons JSON asli untuk endpoint yang kamu tambah.
