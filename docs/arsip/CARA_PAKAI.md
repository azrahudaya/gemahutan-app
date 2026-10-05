> **Arsip, tidak berlaku lagi.** Dipindahkan ke `docs/arsip/` pada 3 Oktober 2026. Acuan yang
> berlaku: `docs/VISI_DAN_RUANG_LINGKUP.md`. Isi di bawah boleh dibaca untuk sejarah, tetapi
> jangan dijadikan dasar tugas.

# Cara Pakai: Web, Android, Package

Disusun 23 September 2026. Web dibangun ulang dari nol. Android dan
package belum ada di repo, rancangan ini berdasarkan
`docs/RENCANA_PRODUK.md`, `docs/CONTRACT_v2.md`, dan API riil.

## 1. Aplikasi Web (Next.js, peramban)

### Siapa yang pakai
Ranger, peneliti, admin, juri, kepala seksi konservasi. Semua
peran cukup peramban modern (Chrome, Edge, Firefox).

### Alur singkat
1. Buka `https://demo.gemahutan.example` (atau localhost:3001 saat
   dev).
2. Klik "Masuk", isi email dan kata sandi.
3. Masuk dasbor sesuai peran:
   - Ranger: lihat ringkasan, unggah/rekam, lihat status.
   - Peneliti: verifikasi deteksi, unduh CSV, bandingkan spesies.
   - Admin: kelola lokasi, perangkat, akun, kalibrasi.
4. Setiap halaman punya status Loading, Kosong, Error, Sukses.

### Yang harus disiapkan sebelum jalan
- `NODE_ENV=production` di image web.
- `PUBLIC_API_URL` menunjuk ke URL API yang valid (path relatif
  kalau satu domain dengan Caddy).
- `CORS_ORIGINS` memuat origin web. Tanpa itu login gagal di
  peramban walau curl API sukses.
- Health: `GET /healthz` 200, `GET /readyz` 200 sebelum dianggap
  hidup.
- Pendaftaran publik hanya saat dev. Sebelum URL publik dipasang,
  `ALLOW_REGISTRATION=false`.

### Yang membatasi
- Butuh jaringan untuk upload, kecuali PWA mode offline (antrean
  lokal + resume). Sekarang baru installable shell.
- Peramban tanpa MediaRecorder tidak bisa merekam dari `/rekam`,
  hanya bisa unggah berkas.
- Tabel besar (>1000 baris) butuh virtual scroll,否则 lag.

## 2. Aplikasi Android (Kotlin native, dalam rancangan)

### Siapa yang pakai
Petugas lapangan yang merekam di hutan jauh dari sinyal. Aplikasi
ini alat tangkap, bukan dasbor.

### Cara kerja
1. Pasang APK debug dari `~/Projects/gemahutan/apps/android`
   (scaffold).
2. Masuk dengan akun ranger. Token JWT disimpan di EncryptedShared
   Preferences.
3. Pilih lokasi (wajib) dan perangkat (opsional) sebelum rekam.
   Lokasi dan perangkat di-cache lokal.
4. Rekam foreground service dengan notifikasi permanen. Format
   rekaman: AAC dalam MPEG-4 (.m4a), 48 kHz mono, 96 kbps.
5. Klik berhenti. Berkas masuk antrean lokal (Room SQLite).
6. Saat online, WorkManager unggah satu per satu lewat endpoint
   `POST /api/v1/recordings`. Token dipakai dari SharedPreferences.
7. Kalau unggah terputus di tengah, OkHttp resume dari byte
   terakhir. Checksum SHA-256 dicocokkan di server.
8. Aplikasi menutup tidak menghapus antrean: rekaman tetap aman
   sampai statusnya "uploaded" di server.

### Yang membatasi
- Tidak menjalankan BirdNET. Inference tetap di server. Android
  hanya alat tangkap.
- GPS dari `FusedLocationProviderClient`, akurasi 10 m. Timestamp
  server adalah waktu unggah, timestamp rekaman adalah waktu GPS.
- Mode pesawat total: rekam jalan, unggah tunggu sinyal. Audio
  tetap disimpan lokal terenkripsi.
- Baterai: rekam 30 menit dengan layar mati menghabiskan sekitar
  8 sampai 12 persen baterai di HP kelas menengah.

### Yang harus disiapkan sebelum jalan
- Izin: `RECORD_AUDIO`, `ACCESS_FINE_LOCATION`, `FOREGROUND_SERVICE`,
  `FOREGROUND_SERVICE_MICROPHONE`, `POST_NOTIFICATIONS`, `INTERNET`.
- Foreground service type `microphone` sesuai Android 14.
- `minSdk` 26 (Android 8) untuk EncryptedSharedPreferences tanpa
  legacy, `targetSdk` 34.
- `kotlinx.serialization` untuk JSON, `Retrofit` + `OkHttp` untuk
  HTTPS, `Room` untuk antrean.

## 3. Package Python (ML pipeline, `pip install`)

### Siapa yang pakai
Peneliti dan kontributor yang ingin melatih ulang classifier
Track B atau menjalankan pipeline di mesin mereka sendiri.

### Cara kerja
1. Pasang dari GitHub setelah versi stabil:
   ```
   pip install gemahutan-ml
   ```
   Sumber paket: `setup.py` di root repo atau `pyproject.toml`.
2. Impor di skrip:
   ```python
   from gemahutan.ml import CascadeEngine, FieldEvaluator
   engine = CascadeEngine()
   deteksi = engine.predict("rekaman.wav", lat=-6.2, lon=106.8)
   ```
3. Atau pakai CLI:
   ```
   gemahutan-train --epochs 300 --hidden 256 --lr 0.001 --seed 42
   gemahutan-eval --checkpoint-dir ml/checkpoints --field
   gemahutan-degrade --in ml/data/audio --out ml/data/degraded
   ```

### Apa yang dapat dilakukan
- Latih ulang Track B dengan seed tetap, `--resume` dari
  checkpoint.
- Evaluasi per spesies (precision, recall, F1, AUC-PR, support).
- Evaluasi lapangan (Xeno-canto, iNaturalist, pengecoh).
- Buat tangga degradasi (angin, hujan, kota, jarak).
- Sinkronkan threshold ke basis data lewat `make sync-thresholds`.

### Yang membatasi
- CPU only by default (numpy MLP). Tidak butuh PyTorch.
- BirdNET-Analyzer dipasang otomatis oleh pip, sekitar 250 MB.
- TensorFlow tidak dipasang (kecuali worker image). Worker yang
  perlu, host tidak.
- Paket wheel hanya untuk Linux x86_64 dan macOS arm64 sampai
  ditulis ulang untuk Windows.

### Yang harus disiapkan
- Python 3.11 atau lebih baru.
- `librosa`, `numpy`, `scipy`, `scikit-maad`, `soundfile` (otomatis
  oleh pip).
- Seed tetap (default 42) supaya hasil reproducible.
- `resampy` wajib agar birdnetlib bisa membaca mp3 44,1 kHz
  (pelajaran dari sesi sebelumnya, pernah lupa dan worker
  bingung).

## 4. Perbandingan tiga permukaan

| Aspek | Web | Android | Package Python |
|---|---|---|---|
| Tujuan | Kelola data, verifikasi, dasbor | Tangkap audio lapangan | Latih/evaluasi model |
| User utama | Ranger, peneliti, admin | Ranger | Peneliti ML |
| Alat | Peramban modern | HP Android 8+ | Terminal Python 3.11+ |
| Akses | Token JWT | Token JWT (sama) | Tidak perlu (lokal) |
| Internet | Wajib untuk upload | Tunda sampai online | Tidak wajib |
| Inference | Server | Tidak, kirim ke server | Lokal (kalau.engine() dipanggil) |
| Mode offline | Terbatas (PWA shell) | Penuh (antrean lokal) | Tidak relevan |
| Instalasi | URL + login | APK dari Play Store / F-Droid | pip install |
| Update | Setiap deploy | Play Store / F-Droid | pip install -U |

## 5. Hubungan ketiganya

Ketiganya bertemu di satu API yang sama (`apps/api`). Token JWT
diterima dari semua sisi. Skema data unggahan identik: site_id
wajib, device_id opsional, recorded_at opsional. Tidak ada
duplikasi pipeline.

Web adalah control plane. Android adalah input plane. Package
adalah development plane. Server adalah satu-satunya tempat
inference BirdNET dan classifier lokal berjalan.

## 6. Yang harus dibangun duluan

Urutan:

1. Web dasbor + unggah (M1-M3 dari `docs/RENCANA_4_WORKSTREAM.md`).
2. Package Python untuk evaluator dan trainer (supaya peneliti
   bisa kontribusi tanpa setup repo lengkap).
3. Android scaffold (M4) baru setelah web stabil.
4. Edge agent untuk AudioMoth menyusul setelah Android jalan.

Android bukan prasyarat web. Package bukan prasyarat Android.
Mereka bertiga terhubung lewat API, bukan lewat pustaka bersama.
