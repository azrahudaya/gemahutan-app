> **Arsip, tidak berlaku lagi.** Dipindahkan ke `docs/arsip/` pada 3 Oktober 2026. Acuan yang
> berlaku: `docs/VISI_DAN_RUANG_LINGKUP.md`. Isi di bawah boleh dibaca untuk sejarah, tetapi
> jangan dijadikan dasar tugas.

# Rencana Produk GemaHutan

Diperbarui: 21 September 2026

Dokumen ini melanjutkan sesi 21 September pukul 15:38 yang terputus sebelum
rencananya tersimpan. Isinya keputusan bentuk produk, penguatan sisi riset
(Fase 3), prioritas dari audit mandiri 21 September, dan daftar persiapan.

Angka di dokumen ini diperiksa ulang 21 September 2026 lewat perintah nyata:
API 57 test lulus, worker 25 test lulus, web 57 test lulus, `tsc --noEmit`
bersih, commit `3aac745`, worktree bersih. Temuan lama dan keadaannya sekarang
ada di `docs/AUDIT_AND_PLAN.md`. Checklist lomba ada di `docs/CHECKLIST_SUBMIT.md`.

## 1. Bentuk produk yang dipilih

GemaHutan tidak dipaksa menjadi satu bentuk. Paling kuat kalau dibagi tiga
lapisan, masing-masing mengerjakan satu hal.

Posisi satu baris:

> GemaHutan adalah platform pemantauan bioakustik dengan web control plane,
> Android field capture, dan edge agent untuk perangkat perekam.

### 1.1 Web sebagai control plane dan pusat riset

Cocok untuk dashboard pengelola kawasan, review dua peneliti, adjudication,
peta dan laporan, manajemen perangkat, manajemen dataset, kalibrasi, monitoring
mutu model, serta audit dan ekspor.

Kelebihannya: tanpa instalasi, cocok untuk banyak peran, mudah dipakai juri dan
peneliti, operasi terpusat, UI dan pipeline cepat diperbarui.

Batasnya, dan ini yang menentukan bentuk kedua:

- Tidak cocok untuk rekaman panjang saat layar mati.
- Browser membatasi mikrofon, izin, baterai, dan proses di latar belakang.
- Tidak ideal untuk USB audio, BLE, serial, GPS, dan perangkat khusus.
- PWA sekarang hanya installable. Service worker menyimpan aset statis, bukan
  antrean rekaman, jadi belum ada mode offline sungguhan.
- Unggahan yang terputus belum bisa dilanjutkan.
- Kontrol perangkat lapangan belum cukup dalam.

Kesimpulan: web tetap produk utama untuk pengelolaan dan riset, tetapi browser
jangan dijadikan perekam lapangan utama.

### 1.2 Android sebagai alat capture lapangan

Fitur yang perlu ada: pendaftaran dan pairing perangkat dengan lokasi, rekam
foreground service, rekam latar belakang dengan notifikasi permanen,
penyimpanan lokal terenkripsi, antrean unggah lokal, resume unggah, checksum
berkas, GPS dan timestamp, metadata perangkat, pemeriksaan mutu audio sebelum
unggah, mode offline, sinkronisasi saat jaringan kembali, tombol berhenti
darurat, serta pengaturan durasi dan sample rate.

Teknologi: Kotlin native kalau targetnya Android saja dan butuh akses hardware
yang stabil. Flutter hanya kalau nanti benar-benar perlu iOS, dan itu berarti
rencana di bagian E `docs/AUDIT_AND_PLAN.md` perlu diperbarui karena di sana
masih tertulis Flutter.

Tahap awal Android hanya merekam dan mengirim ke server. Jangan menjalankan
BirdNET penuh di perangkat.

### 1.3 Edge agent untuk perangkat IoT

Sasarannya Raspberry Pi, Orange Pi, industrial PC, gateway di lokasi hutan,
mikrofon array USB, dan recorder seperti AudioMoth yang menulis berkas ke SD
card. Bentuknya bukan aplikasi untuk pengguna akhir, tetapi agen bernama
`gemahutan-edge` dengan tugas: membaca konfigurasi, mendeteksi input audio,
memotong audio 30 atau 60 detik, menambahkan timestamp dan metadata, menghitung
checksum, menyimpan antrean lokal SQLite, mengirim berkas saat jaringan
tersedia, mengirim status dan metrik perangkat, menjalankan quality check, dan
nanti inference lokal.

Setiap berkas membawa `sha256`, `device_id`, `recorded_at`,
`firmware_version`, `sample_rate`, `channel_count`, dan `location_id`. Audio
tidak dikirim lewat MQTT. MQTT hanya untuk metadata, status, perintah,
heartbeat, dan konfigurasi. Berkas audio lewat HTTPS atau presigned upload,
dengan TLS dan device credential.

### 1.4 Yang tidak dikerjakan

- ESP32 bukan target inference. Perangkat sekelas itu cocok jadi sensor,
  pengendali, atau pengirim status.
- Android bukan salinan dashboard web.
- Inference resmi tetap di server. Edge agent menyusul setelah ada benchmark
  hardware.
- Edge agent tidak langsung menjalankan inference, mulai dari capture,
  quality check, dan antrean lokal.

## 2. Urutan kerja

### Tahap 1, perkuat backend riset

Kalibrasi perangkat, review dua peneliti dan adjudication, dataset versioning,
provenance dan lisensi, model release registry, kalibrasi confidence, metrik
drift, audit log.

Alasannya: kalau Android dibuat lebih dulu, aplikasi hanya mengumpulkan audio
tanpa sistem yang menjaga mutu data. Untuk lomba dan untuk klaim riset, sisi
inilah yang menentukan.

### Tahap 2, Android capture app

Fokus ke capture, antrean offline, GPS, metadata, unggah resumable, pairing
perangkat, status perangkat, dan quality check audio.

### Tahap 3, edge package

Mulai dari Raspberry Pi, mikrofon USB atau recorder berbasis berkas, antrean
SQLite, unggah HTTPS, status MQTT, service systemd, device certificate, berkas
konfigurasi, dan health endpoint lokal. Setelah stabil baru tambah VAD lokal,
quality scoring lokal, inference lokal, dan buffering berhari-hari.

## 3. Fase 3, penguatan sisi riset

Tujuh butir di bawah ini yang membedakan aplikasi demo dari produk riset.

### 3.1 Workflow kalibrasi perangkat

Sekarang perangkat hanya punya kolom jumlah kanal, jarak mikrofon, dan level
acuan. Itu belum menjadi workflow kalibrasi.

Tabel `device_calibration_sessions`: `id`, `device_id`, `started_at`,
`completed_at`, `operator_id`, `method`, `status`, `environment`, `notes`,
`created_at`. Status: `draft`, `running`, `passed`, `failed`, `expired`.

Tabel `calibration_measurements`: `calibration_id`, `channel_index`,
`gain_offset_db`, `delay_offset_samples`, `noise_floor_db`, `clipping_rate`,
`sample_rate_measured`, `valid`.

Yang diukur: selisih gain antar kanal, selisih delay antar kanal, noise floor,
clipping, sample rate aktual, serta kanal mati atau terlalu lemah.

Setiap deteksi harus membawa `calibration_id`, `calibration_version`,
`calibration_status`, dan `calibration_age_days`. Worker tidak boleh menghitung
azimuth kalau kalibrasi gagal, kedaluwarsa, jumlah kanal berubah, geometri
perangkat belum lengkap, atau delay antar kanal melewati batas.

Array empat kanal segaris masih ambigu antara depan dan belakang. Geometri 2D
(persegi atau L) yang mengurangi ambiguitas itu.

Kriteria lulus awal: galat arah median di bawah 5 derajat pada kondisi bersih,
P95 di bawah 10 derajat, delay residual antar kanal di bawah batas untuk sample
rate perangkat, tidak ada kanal clipping terus-menerus, dan hasilnya bisa
diulang dengan angka yang konsisten.

Jangkauan dipisah dari kalibrasi arah. Jangkauan butuh sumber uji dengan level
diketahui, jarak diketahui, kondisi lingkungan dicatat, level referensi, dan
metode pengukuran yang konsisten. Jangkauan tidak ditampilkan hanya karena
`reference_distance_m` sudah diisi; profil kalibrasinya harus berstatus
`passed`.

### 3.2 Confidence dan uncertainty

Threshold per spesies menjawab "berapa nilai minimum agar deteksi diterima".
Itu bukan kalibrasi confidence, dan belum menjawab "kalau model bilang 0,8,
apakah sekitar 80 persen kejadian seperti itu benar".

Kalibrasi memakai dataset khusus yang tidak dipakai training. Yang diukur:
reliability diagram, Expected Calibration Error, Brier score, log loss,
precision dan recall per spesies, lalu kalibrasi per kondisi audio, per
perangkat, dan untuk kelas negatif. Metode awal: temperature scaling, isotonic
regression kalau data cukup, Platt scaling untuk kasus biner per spesies.

Keluaran deteksi sebaiknya:

```json
{
  "raw_score": 0.81,
  "calibrated_probability": 0.74,
  "decision_threshold": 0.60,
  "confidence_band": "medium",
  "calibration_version": "cal-2026-09-01"
}
```

Keluaran lokalisasi membawa beberapa sinyal sekaligus, yaitu residual
GCC-PHAT, rasio puncak terbaik terhadap puncak alternatif, SNR, jumlah kanal
aktif, kesamaan hasil antar window, ambiguitas arah kembar, konsistensi antar
perangkat, dan mutu kalibrasi:

```json
{
  "azimuth_deg": 60.0,
  "azimuth_interval_deg": [57.5, 62.5],
  "azimuth_confidence": 0.82,
  "ambiguous_azimuths_deg": [300.0],
  "quality": "usable",
  "quality_flags": []
}
```

Angka `azimuth_confidence` sekarang masih skor heuristik. Jangan disebut
probabilitas sebelum benar-benar dikalibrasi.

### 3.3 Review dua peneliti dan adjudication

Status `correct`, `incorrect`, `uncertain` saja belum cukup, dan sekarang masih
bisa ditimpa reviewer berikutnya sehingga keputusan pertama hilang.

Tabel `detection_reviews`: `detection_id`, `reviewer_id`, `label`,
`confidence`, `comment`, `reviewed_at`, `evidence_clip_start`,
`evidence_clip_end`, `review_round`. Reviewer pertama dan kedua tidak boleh
melihat keputusan satu sama lain sebelum mengirim review.

Kalau hasil berbeda, sistem membuka `review_case` berstatus `open`, `assigned`,
`adjudicated`, `closed`. Adjudicator memilih label final, menulis alasan
menandai reviewer yang perlu catatan, menentukan apakah klip masuk dataset gold
dan apakah kasusnya jadi contoh sulit.

Mutu reviewer diukur dengan agreement rate, Cohen's kappa untuk dua reviewer,
persentase kasus yang masuk adjudication, waktu rata-rata review, agreement per
spesies, dan agreement per kondisi audio. Reviewer baru diuji terhadap gold set
sebelum boleh melakukan review produksi.

### 3.4 Monitoring drift dan false positive

Akurasi offline saja tidak cukup. Setelah aplikasi dipakai, bangun pipeline
monitoring dari hasil review manusia.

Per rekaman disimpan: RMS, perkiraan SNR, clipping ratio, durasi, sample rate,
jumlah kanal, noise floor, firmware perangkat, lokasi, waktu dan musim, cuaca
kalau tersedia, dan versi model.

Drift audio dibandingkan dengan data training memakai PSI untuk distribusi, KS
test untuk fitur numerik, jarak embedding, dan persentase audio gagal decode.
Drift hasil model dipantau lewat jumlah deteksi per jam, rasio audio tanpa
deteksi, jumlah spesies unik, proporsi kelas negatif, distribusi confidence,
false positive dan false negative dari review, serta error per perangkat,
lokasi, dan kondisi audio.

Trigger review: false positive naik melewati batas, satu perangkat menghasilkan
distribusi yang jauh berbeda, audio gagal decode meningkat, confidence
mendekati 1 untuk hampir semua deteksi, satu spesies mendominasi secara tidak
wajar, atau distribusi embedding bergeser jauh dari dataset training.

Hasil monitoring harus membuat `drift_alert` yang ditindaklanjuti, bukan grafik
yang dibiarkan.

### 3.5 Dataset versioning

Dataset tidak lagi berupa folder dan CSV yang berubah diam-diam.

`dataset_versions`: `id`, `name`, `version`, `created_at`, `created_by`,
`manifest_sha256`, `status`, `notes`.

`dataset_items`: `dataset_version_id`, `recording_id`, `storage_key`,
`file_sha256`, `label`, `label_source`, `split`, `eligible_for_training`,
`exclusion_reason`, `license_status`.

`training_runs`: `dataset_version_id`, `model_type`, `checkpoint_sha256`,
`normalization_sha256`, `config_json`, `seed`, `started_at`, `finished_at`,
`metrics_json`, `status`.

Aturannya: version dataset tidak bisa diubah, manifest punya hash, pembagian
train, validation, test disimpan permanen, berkas dari satu rekaman tidak
tersebar ke split berbeda, sumber yang sama atau suara turunannya diperiksa agar
tidak bocor, model produksi hanya berasal dari dataset version yang disetujui,
dan setiap model release menyimpan ID serta hash artefaknya.

Setiap deteksi membawa jejak:

```json
{
  "model_release": "track-b-2026-09-21-01",
  "dataset_version": "dataset-2026-09-15",
  "checkpoint_sha256": "...",
  "threshold_version": "thresholds-2026-09-15",
  "preprocessing_version": "audio-v3"
}
```

Tanpa itu, hasil enam bulan lalu sulit dipertanggungjawabkan.

### 3.6 Pelacakan sumber dan lisensi

Tabel `recordings` perlu kolom provenance: `source_type` (user_upload,
xeno_canto, inaturalist, field_recording, demo), `source_url`,
`source_record_id`, `creator_name`, `license_name`, `license_url`,
`derivatives_allowed`, `commercial_use_allowed`, `attribution_required`,
`consent_status`, `training_eligible`, `retention_policy`,
`provenance_verified_at`.

Aturan operasional: lisensi tidak diketahui berarti tidak boleh masuk training,
lisensi ND tidak boleh dipotong atau dijadikan dataset turunan, rekaman
pengguna privat secara default, rekaman publik harus punya atribusi, ekspor
dataset membawa atribusi, dan dataset training harus bisa menjawab asal setiap
klip. Metadata lisensi tidak cukup disimpan di `ATTRIBUTION.csv`; harus masuk
database dan manifest dataset.

### 3.7 Validasi lokalisasi pada kondisi sulit

Validasi sekarang terlalu bersih. Perlu benchmark dengan ground truth.

Kondisi arah: azimuth 0, 30, 60, 90, 120, 180, 240, 300 derajat; jarak 5, 10,
25, 50 meter; array 2D dan array garis; dua sampai empat kanal; kanal tertukar;
satu kanal mati; gain antar kanal tidak sama; clock drift.

Kondisi suara: SNR 20, 10, 0, dan minus 5 dB; gema; pantulan; hujan; angin;
kebisingan jalan; dua burung bersamaan; suara manusia; suara serangga dan daun;
sumber bergerak.

Kondisi perangkat: sample rate berbeda, firmware berbeda, jarak mikrofon
berbeda, orientasi array berbeda, suhu dan kelembapan berbeda, jaringan terputus
di tengah unggah.

Metrik: median absolute angular error, P95 angular error, persentase hasil di
dalam interval toleransi, false direction rate, ambiguity detection rate, range
error, serta error per perangkat, per SNR, dan per kondisi gema.

Release gate: arah bersih median di bawah 5 derajat, P95 bersih di bawah 10
derajat, SNR 0 dB median di bawah 15 derajat. Kalau syarat tidak tercapai,
hasilnya diberi status `insufficient_quality`, bukan dipaksa menjadi angka.

## 4. Prioritas dari audit mandiri 21 September 2026

Temuan lengkapnya ada di sesi; ringkasan ini supaya tidak hilang. Semuanya
diverifikasi dari source dan runtime pada 21 September, bukan dari audit lama.

### P0, sebelum dipakai banyak pengguna

| # | Temuan | Bukti |
|---|---|---|
| 1 | Semua pengguna yang login bisa membaca data pengguna lain: rekaman, deteksi, audio, daftar job, ekspor, lokasi, statistik sistem | `apps/api/app/routers/detections.py:21,125,166`, `apps/api/app/routers/exports.py:49,98`, `apps/api/app/routers/recordings.py:418`. Diuji dengan akun ranger baru, semuanya balas 200 |
| 2 | Autentikasi terlalu lemah untuk aplikasi publik: password satu karakter diterima, tidak ada verifikasi email, lupa sandi, ganti sandi, MFA; `is_active` tidak diperiksa `_resolve_user()`; registrasi default terbuka | `apps/api/app/schemas/auth.py`, `apps/api/app/routers/auth.py`, `apps/api/app/deps.py`, `apps/api/app/config.py` |
| 3 | Refresh token tidak dirotasi, token lama tetap sah sampai tujuh hari | `apps/api/app/routers/auth.py:99-123` |
| 4 | Token dikirim lewat URL pada audio dan SSE, bisa masuk access log, riwayat browser, dan monitoring | `apps/api/app/deps.py:33-46,79-87`, `apps/api/app/routers/jobs_stream.py` |

### P1, sebelum pilot lapangan dan sebelum URL diumumkan

| # | Temuan | Bukti |
|---|---|---|
| 5 | Validasi audio hanya ekstensi dan MIME; berkas teks bernama `.wav` diterima 201, masuk storage, dan job antre | `apps/api/app/routers/recordings.py:44-88` |
| 6 | Operasi sinkron di endpoint async: `file.read()`, boto3 unggah baca hapus | `apps/api/app/routers/recordings.py:69-88`, `apps/api/app/services/storage.py` |
| 7 | Belum ada rate limit untuk unggah, batch, spektrogram, ekspor, retry, SSE, daftar job, laporan | `apps/api/app/routers/*` |
| 8 | Perangkat tidak divalidasi terhadap lokasi rekaman, PATCH `device_id` bebas | `apps/api/app/routers/recordings.py:91-101,500-550` |
| 9 | Hapus rekaman tidak atomik, audio yatim bisa tertinggal | `apps/api/app/routers/recordings.py:584-604` |
| 10 | Tidak ada riwayat perubahan dan riwayat verifikasi | model verifikasi hanya menyimpan kondisi terakhir |
| 11 | Klaim loop verifikasi ke data latih belum otomatis, pipeline masih batch manual | `ml/data/from_verifications.py` |
| 12 | Lokalisasi masih estimasi arah dari array mikrofon, bukan pelacakan posisi | lihat bagian 3.1 dan 3.7 |
| 13 | Belum ada monitoring model produksi: drift, false positive per lokasi, hash checkpoint per deteksi, rollback | `apps/api/app/services/model_status.py` |
| 14 | Dependensi JS punya 4 kerentanan critical atau high: MapLibre, Next.js, PostCSS, sharp | `apps/web/package.json` |
| 15 | Docker build tidak memakai lockfile web, versi dependency bisa berbeda dari CI | `apps/web/Dockerfile` |
| 16 | Header keamanan produksi belum lengkap: CSP, Permissions-Policy, frame-ancestors, CORS spesifik | `deploy/` |
| 17 | Mode deploy bawaan tidak menjalankan worker, unggahan baru tidak diproses | `deploy/docker-compose.prod.yml` |

### P2, reliability, fitur, dan UI

`/readyz` selalu 200 (`apps/api/app/main.py:113`) dan health check worker hanya
`print('worker alive')` (`apps/worker/Dockerfile:35`); backup belum terenkripsi,
belum offsite, dan restore object storage belum diuji; ekspor dan beberapa daftar
tanpa batas skala; audio belum mendukung HTTP Range; observability belum ada
structured logging, correlation ID, dan alert; belum ada lupa sandi, ganti sandi,
dan halaman profil; PWA belum offline sungguhan; unggah batch belum resumable dan
belum idempotent; riwayat model dan dataset belum cukup untuk reproduksi; lisensi
belum jadi bagian model data; verifikasi ahli masih satu langkah; satu target
sentuh di `/upload` masih 100x18 piksel; audit keyboard baru membuktikan elemen
fokus pertama, belum seluruh tab order; belum diuji zoom 200 persen, TalkBack,
forced colors, Safari iOS, dan izin mikrofon ditolak lalu diberikan kembali.

## 5. Yang perlu disiapkan dari sekarang

Urutannya dari yang bisa dikerjakan tanpa menunggu siapa pun, lalu aset yang
harus dikumpulkan, lalu keputusan yang hanya bisa diambil pemilik produk.

### 5.1 Bisa dikerjakan sekarang, tanpa keputusan luar

1. Tutup P0 nomor 1 sampai 4. Ini yang menentukan apakah URL boleh dibagikan,
   dan jadwal lomba menaruh URL pada 6 sampai 9 Oktober 2026.
2. Perbaiki tiga hal kecil yang menahan kepercayaan: lockfile di Docker build web
   (`npm ci` dengan `package-lock.json`), `/readyz` yang benar-benar memeriksa
   database, Redis, storage, migrasi, dan worker, serta health check worker yang
   membaca heartbeat.
3. Validasi audio dengan `ffprobe` sebelum masuk storage, plus batas durasi,
   kanal, sample rate, dan ukuran batch.
4. Rapikan dokumen status yang sekarang salah: angka test di
   `docs/AUDIT_AND_PLAN.md` (tertulis 24 worker dan 51 web, hasil periksa ulang
   25 dan 57) dan baris Fase 11 di `PROGRESS.md` yang masih `IN_PROGRESS`
   padahal halamannya sudah jalan sejak commit `9b5dee2`.
5. Siapkan cabang kerja Fase 3 (`feat/fase3-riset`) dan migrasi pertama untuk
   `device_calibration_sessions` dan `calibration_measurements`, supaya
   pekerjaan skema tidak menumpuk di worktree `main` yang sekarang bersih.
6. Jalankan `ops/verify_features.py` dan `ops/security_check.py` dari repo
   bersih sekali jalan penuh. Ini masih utang yang tercatat di
   `docs/AUDIT_AND_PLAN.md` bagian D.

### 5.2 Aset dan data yang harus dikumpulkan sebelum fitur Fase 3 dibangun

Fitur kalibrasi, confidence, review, dan validasi lokalisasi tidak bisa
dibuktikan tanpa data ini. Mengumpulkannya lebih lama daripada menulis kodenya,
jadi mulai sekarang.

1. Rekaman kalibrasi arah dengan ground truth: azimuth 0 sampai 330 derajat
   dengan langkah 30, jarak 5, 10, 25, dan 50 meter, minimal array 2D dan array
   garis, dua sampai empat kanal.
2. Rekaman kondisi sulit: SNR 20, 10, 0, dan minus 5 dB, lalu gema, hujan,
   angin, dua burung bersamaan, dan sumber bergerak.
3. Gold set kecil, sekitar 100 klip, yang labelnya sudah disepakati, untuk
   menguji reviewer baru dan mengukur agreement.
4. Dataset kalibrasi confidence yang tidak dipakai training, dipisah per
   kondisi audio dan per perangkat.
5. Rekaman lapangan asli. Sampai sekarang seluruh audio berasal dari
   Xeno-canto, korpus lapangan turunan, dan klip demo. Ini kekurangan yang sudah
   ditulis apa adanya di `docs/AUDIT_AND_PLAN.md` bagian D, dan untuk lomba
   kategori riset ini yang paling mudah dipertanyakan juri.
6. Kalau targetnya menampilkan arah datang pada rekaman asli, jalur pemrosesan
   harus berhenti menyamakan audio ke satu kanal. Selama itu belum berubah,
   perangkat berkanal banyak pun tidak akan menghasilkan arah.

### 5.3 Keputusan yang hanya bisa diambil pemilik produk

1. Mode deploy: VPS dengan worker selalu jalan, atau demo tanpa worker dengan
   pembatasan unggahan yang ditulis jelas di halaman demo. Ini menentukan apa
   yang boleh dijanjikan ke juri.
2. Alamat publik dan kredensial deploy. Sekarang masih ditunda di
   `NEEDS_FROM_YOU.md`, dan lomba meminta URL pada 6 sampai 9 Oktober 2026.
3. Repo publik atau privat saat submit. Sekarang tertulis privat.
4. Android pakai Kotlin native atau Flutter. Rencana di `AUDIT_AND_PLAN.md`
   masih Flutter; keputusan ini menentukan seluruh kode Android.
5. Apakah klaim lokalisasi tetap ditonjolkan pada proposal, atau ditulis sebagai
   estimasi arah dengan batas ilmiahnya. Saran saya yang kedua.

### 5.4 Berkas lomba USB 2026

Rincian syarat dan jadwalnya ada di `docs/CHECKLIST_SUBMIT.md`. Yang belum ada
sama sekali: proposal PDF final, PPT maksimal 10 halaman, video YouTube unlisted
maksimal 10 menit resolusi 1920x1080, surat pernyataan orisinalitas bermaterai,
poster, tag git `submit-usb2026`, dan URL publik.

Aset yang sudah siap: grafik 11 berkas di `docs/proposal/figures`, tangkapan
layar 13 berkas di `docs/proposal/screenshots`, data pendukung di
`docs/proposal/data`, manual, dan lisensi pihak ketiga di `docs/LICENSES.md`.

## 6. Gate sebelum URL dibagikan

Urutannya: tutup pendaftaran akun (`ALLOW_REGISTRATION=false`), ganti kata sandi
akun contoh, set `ENVIRONMENT=production`, jalankan `ops/security_check.py`,
lalu `ops/verify_features.py`. Keduanya harus lulus sebelum URL dibagikan, dan
sebelum itu P0 nomor 1 sampai 4 harus sudah ditutup.

## 7. Cara memeriksa ulang dokumen ini

```bash
cd ~/Projects/gemahutan
docker compose ps --format '{{.Service}} {{.Status}}'
docker compose exec -T api python -m pytest tests/ -q      # harapan: 57 lulus
docker compose exec -T worker python -m pytest tests/ -q   # harapan: 25 lulus
cd apps/web && npx tsc --noEmit && npx vitest run           # harapan: 57 lulus
python3 ops/verify_features.py
python3 ops/security_check.py
```
