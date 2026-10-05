# API Reference. GemaHutan

Base URL pengembangan: `http://localhost:8000`. Produksi: `https://gemahutan.site/api/v1/...`
lewat Caddy; `/docs` dan `/openapi.json` mati di produksi. Semua endpoint selain auth dan health butuh header
`Authorization: Bearer <access_token>`.

> Catatan 21 September 2026: berkas ini belum diperbarui penuh untuk Fase 2. Endpoint
> perangkat, akun, batch unggahan, progres job, siaran status, dan lokalisasi dijelaskan
> di [MANUAL.md](MANUAL.md) bagian 12, halaman `/dokumentasi` di aplikasi, dan versi
> hidupnya di `/openapi.json` serta `/docs` saat mode pengembangan.

## Auth

### POST /api/v1/auth/register
```json
Request:  {"email": "user@example.com", "password": "secret"}
Response: {"id": 1, "email": "...", "role": "ranger", "created_at": "..."}
```
409 kalau email sudah terdaftar. **Tertutup di produksi** (`ALLOW_REGISTRATION=false`):
akun petugas dibuat admin. Endpoint undangan akun oleh admin belum ada (target Tahap 1,
lihat `docs/VISI_DAN_RUANG_LINGKUP.md`).

### POST /api/v1/auth/forgot-password
`{"email": "..."}`. Selalu 202 dengan pesan yang sama, terdaftar atau tidak. Tautan atur
ulang dikirim lewat SMTP (`SMTP_HOST`, `SMTP_FROM`, dst.). Tanpa SMTP di produksi,
pengiriman dicatat gagal di log.

### POST /api/v1/auth/reset-password
`{"token": "...", "password": "..."}` (sandi 8 sampai 128 karakter). Token sekali pakai.
400 untuk token salah maupun kedaluwarsa, pesannya sama.

### POST /api/v1/auth/tamu
Tersembunyi dari skema. Hanya dipanggil server web untuk "Coba contoh" di halaman depan,
dengan header `x-tamu-rahasia`. Akun tamu dibatasi daftar izin di
`apps/api/app/services/tamu.py`, maksimal 10 unggahan per 24 jam, dihapus setelah 24 jam.

### POST /api/v1/auth/login
```json
Request:  {"email": "...", "password": "..."}
Response: {"access_token": "...", "refresh_token": "...", "token_type": "bearer"}
```

### POST /api/v1/auth/refresh
```json
Request:  {"refresh_token": "..."}
Response: {"access_token": "...", "refresh_token": "...", "token_type": "bearer"}
```

### POST /api/v1/auth/logout
Bukan lagi stateless: `jti` access dan refresh token dicatat di Redis sampai kedaluwarsa,
jadi token yang sudah logout ditolak walau masa berlakunya belum habis. Kirim
`{"refresh_token": "..."}` supaya refresh token ikut dicabut.
Response: `{"message": "Logged out successfully"}`

### GET /api/v1/me
Info user aktif, termasuk `name` dan `role`.

## Recordings

### POST /api/v1/recordings
Multipart: `file` (wav, mp3, flac, ogg, m4a, aac, opus, webm, maksimal 200 MB), `site_id`, `device_id?`, `recorded_at?`.
- 400 tipe atau ekstensi tidak didukung, atau berkas kosong.
- 413 kalau melebihi 200 MB.
- 201 kalau job masuk antrean, 202 kalau berkas tersimpan tapi antrean gagal (`queue_error` berisi alasannya).

### GET /api/v1/recordings
Query: `site`, `device`, `species` (id), `species_q` (cari nama ilmiah atau nama umum),
`min_conf`, `status` (pending, processing, done, failed), `from`, `to` (YYYY-MM-DD),
`page`, `page_size` (maksimal 100).

Response: `{items, total, page, page_size, total_pages}`. Setiap item punya `site_name`
dan `detection_count`. Tanggal yang tidak valid dijawab 400, nilai status yang tidak
dikenal dijawab 422.

### GET /api/v1/recordings/{id}
Detail satu rekaman.

### GET /api/v1/recordings/{id}/detections
Daftar deteksi dengan nama spesies, confidence, rentang waktu, engine, dan status verifikasi.

### GET /api/v1/recordings/{id}/audio
Stream berkas audio asli dari MinIO untuk elemen `<audio>`. Token boleh lewat query
`?token=` karena elemen audio tidak bisa menyetel header. 404 kalau berkas tidak ada di storage.

### GET /api/v1/recordings/{id}/indices
Indeks soundscape satu rekaman. 404 kalau worker belum menghitungnya.
```json
{"recording_id": 11, "aci": 812.4, "ndsi": 0.62, "adi": 0.55, "bi": 214.1,
 "computed_at": "...", "caveat": "Indeks soundscape adalah indikator pelengkap, bukan proxy tunggal biodiversitas."}
```

### GET /api/v1/recordings/{id}/spectrogram
PNG mel spectrogram dengan colormap magma.
- 404 rekaman tidak ada atau audionya tidak ada di storage
- 415 format audio tidak dikenali decoder
- 422 berkas audio kosong

## Detections

### POST /api/v1/detections/{id}/verify
```json
Request:  {"status": "correct|incorrect|uncertain"}
Response: {"message": "Verification saved"}
```
Menyimpan siapa yang memverifikasi dan kapan. Hasil verifikasi adalah bahan latih untuk Track B.

## Species

### GET /api/v1/species
Daftar spesies dengan `common_name_id`, `common_name_en`, `iucn_status`, `ebird_code`,
`default_threshold`, dan `detection_count`.

### GET /api/v1/species/{id}
Detail satu spesies. 404 kalau tidak ada.

### GET /api/v1/species/{id}/detections
Riwayat deteksi spesies tersebut, terbaru dulu. Query: `limit` (1 sampai 200, default 50).
Tiap baris berisi `detection_id`, `recording_id`, `site_name`, `recorded_at`, `confidence`,
`start_s`, `end_s`, `engine`, dan `verified_status`.

## Sites

### GET /api/v1/sites
Query: `name`, `location` (pencarian sebagian).
Response: list lokasi dengan `latitude`, `longitude`, `location`, `habitat_type`,
`elevation_m`, `description`, `notes`, `status`, `last_recording_at`, plus hitungan
`recordings_count`, `detections_count`, dan `species_count`.

`status` bernilai `active` kalau ada rekaman dalam 180 hari terakhir, selain itu `inactive`.

### GET /api/v1/sites/{id}
Detail satu lokasi. 404 kalau tidak ada.

### POST /api/v1/sites
```json
Request: {
  "name": "Taman Nasional Gunung Gede Pangrango",
  "latitude": -6.7875,
  "longitude": 106.9839,
  "location": "Cibodas, Jawa Barat",
  "habitat_type": "montane_forest",
  "elevation_m": 1500,
  "description": "Hutan pegunungan",
  "notes": "Akses lewat Cibodas"
}
Response: 201 dengan objek lokasi lengkap
```
- `latitude` dan `longitude` harus diisi bersamaan, kalau tidak 400.
- Nama duplikat 409.

## Stats

### GET /api/v1/stats/overview
`{recordings, detections, species_detected, sites}`

### GET /api/v1/stats/species?limit=20
Spesies terbanyak terdeteksi.

### GET /api/v1/stats/timeline
Jumlah deteksi per hari.

## Simulasi

### POST /api/v1/simulasi/lokasi
Simulasi perkiraan lokasi tanpa menulis ke basis data. Semua peran petugas boleh
memakainya. Isi permintaan: `alat` (2 sampai 4, masing-masing `{x, y, jenis}`
dalam meter, jenis `larik` atau `satu_kanal`), `sumber` (`[x, y]`), `snr_db`,
`benih`, `sinkron`. Respons memuat arah per alat (azimuth, keyakinan, jarak
estimasi), `perkiraan` (titik hasil triangulasi), `radius_area_m`, `galat_m`,
dan `catatan`. Metode mengikuti proposal Bagian 7.3 (larik 4 mikrofon, GCC-PHAT,
triangulasi kisi).

## Model dan health

### GET /api/v1/model/info
Status nyata, bukan konstanta: `engine`, `status` (up, degraded, unavailable),
`status_detail`, `worker_alive`, daftar `tracks` (A BirdNET dan B classifier lokal)
beserta ketersediaan artefaknya, jumlah threshold yang dimuat, dan metrik evaluasi
dari `ml/reports/metrics.json`.

### GET /healthz
```json
{"status": "ok", "version": "0.1.0",
 "services": {"db": "up", "redis": "up", "storage": "up", "model": "up"},
 "services_required": ["db", "redis", "storage"],
 "model_detail": "worker aktif, engine cascade"}
```
Status `model` dibaca dari heartbeat worker di Redis. HTTP 503 hanya kalau salah satu
layanan wajib (db, redis, storage) mati.

### GET /readyz
`{"status": "ready"}`

## Ekspor

### GET /api/v1/exports/verified
Deteksi yang sudah diverifikasi ahli, untuk diolah di luar aplikasi atau dijadikan
bahan latih. Query: `status` (correct, incorrect, uncertain, all), `site`, `format`
(csv atau json).
Kolom: detection_id, recording_id, site_name, recorded_at, species_scientific,
species_common, confidence, start_s, end_s, engine, engine_version, verified_status,
verified_at.

### GET /api/v1/exports/recordings
Daftar rekaman dengan `detections` dan `verified_detections`. Query: `site`, `format`.
Kolom: recording_id, site_name, status, recorded_at, duration_s, sample_rate,
detections, verified_detections.

## Jobs

### GET /api/v1/jobs
Query: `recording_id`, `status` (pending, running, done, failed). Dipakai UI untuk
menampilkan pesan kegagalan dan tombol proses ulang.

### POST /api/v1/jobs/{id}/retry
Tandai job pending lalu masukkan ulang ke antrean. 503 kalau antrean Redis gagal,
supaya tidak melaporkan sukses palsu.

## Format Error
```json
{"detail": "Pesan error"}
```

## Perilaku keamanan

| Kejadian | Respons |
|---|---|
| Permintaan endpoint data tanpa token | 401 |
| Token dipakai setelah logout | 401, jti dicatat di Redis |
| Refresh token dipakai setelah logout | 401 |
| Enam percobaan login gagal dalam satu menit untuk email dan IP yang sama | 429 dengan header Retry-After |
| Kata sandi salah | 401, disertai sisa percobaan saat tersisa dua atau kurang |

`POST /api/v1/auth/logout` menerima body opsional `{"refresh_token": "..."}`. Kalau
dikirim, refresh token ikut dicabut. Respons memuat `tokens_revoked` berisi jumlah
token yang berhasil dicabut.

