> **Arsip, tidak berlaku lagi.** Dipindahkan ke `docs/arsip/` pada 3 Oktober 2026. Acuan yang
> berlaku: `docs/VISI_DAN_RUANG_LINGKUP.md`. Isi di bawah boleh dibaca untuk sejarah, tetapi
> jangan dijadikan dasar tugas.

# GemaHutan: peta 4 workstream dan audit celah

Disusun 23 September 2026 setelah membaca repo, skill referensi,
serta hasil ukur terakhir. Sumber kebenaran: runtime dan source code,
bukan `docs/AUDIT_AND_PLAN.md`.

Keadaan awal yang ditemukan:
- Stack hidup: api, db, minio, redis, worker semua healthy 12 menit.
- `apps/web/` di worktree lokal terhapus semua (`D apps/web/...` 47 file
  belum di-commit), plus ada `tmp-*` di `src/components/`. Web
  jalan dari image container, bukan dari source lokal.
- Test: API 57 lulus, worker 25, web 57 (database bersih per 21 Sept).
- Model Track B: akurasi uji 0,7156, baseline lapangan tanpa ND 0,7034,
  gabungan berat 0,2817.
- Lokalisasi azimuth 60° galat 0,00° terukur, `range_m` null karena
  perangkat belum dikalibrasi (perlakuan benar).

## 1. Web (Next.js)

### Target
Antarmuka kontrol plane untuk ranger, peneliti, admin, juri. Tampil
utuh di HP, tablet, laptop. Data riil dari API, tidak ada angka
dekoratif. Aksesibilitas terukur.

### Deliverable
- Setiap halaman punya sumber data API yang bisa diaudit.
- Tes vitest di setiap util (`format`, `batch`, `arah`).
- `tsc --noEmit` bersih.
- Lighthouse mobile 90+, tap target minimal 44 px, kontras WCAG.
- PWA installable plus upload offline + background sync (belum ada).

### Urutan kerja
1. Pulihkan worktree web (komit `9b5dee2` sampai HEAD), selesaikan
   `tmp-*`, dan `docker compose build web`.
2. Tambah layer deteksi di peta (`SitesMap` dipakai juga di rekaman
   dan spesies), bukan hanya di dashboard.
3. Tampilkan peta + koordinat di detail rekaman.
4. Pemilih titik di peta pada formulir tambah lokasi.
5. Ekspor PDF dari server untuk `/laporan` (sekitar print browser
   saja).
6. PWA beneran: antrean lokal, resumable upload, sinkron saat
   jaringan kembali.
7. Audit aksesibilitas terulang pada viewport 390 px dan 1440 px.

### Celah yang ditemukan
- Lokasi `range_m` tidak ditampilkan di UI (cuma azimuth). Sumber:
  `/api/v1/recordings/{id}/detections` mengembalikan kolom, tapi
  halaman detail belum merendernya.
- Halaman spesies menampilkan `default_threshold` yang dulu berbeda
  dari `thresholds.json` di 23 dari 25 spesies. `make sync-thresholds`
  wajib di pipeline.
- Filter `page`, `page_size` belum diuji tekan memori untuk ekspor
  besar (`/api/v1/exports/verified`).
- Tidak ada layer deteksi atau sebaran spesies di peta.

## 2. Aplikasi Android

### Target
Alat capture lapangan. Rekam foreground + background, antrean
unggah, resume, GPS, mode offline. Bukan dashboard web.

### Deliverable
- APK debug yang bisa direkam 10 menit, matikan layar, unggah
  setelah jaringan kembali, tidak kehilangan data.
- Background service dengan notifikasi permanen.
- Pasangan perangkat + lokasi sebelum rekam.
- Audit kode: izin, foreground service type, hemat baterai,
  anti-rekam-senyap.

### Urutan kerja
1. Native Kotlin (sesuai `docs/RENCANA_PRODUK.md`). Bukan Flutter
   kecuali ada iOS.
2. Library: MediaRecorder + WorkManager + Room (antrean lokal)
   + OkHttp (resume).
3. Tahap awal: rekam dan kirim ke server. BirdNET tetap di server.
4. Skema data unggahan sama dengan API: `site_id` wajib, `device_id`
   opsional, `recorded_at` dari GPS jam.
5. Tes end-to-end: rekam 30 menit, matikan HP 5 menit, hidupkan,
   lihat antrean pulih.

### Celah
- Belum ada kode sama sekali di repo. Tahap paling awal: scaffold
  proyek Kotlin, struktur modul `capture`, `queue`, `sync`, `ui`.
- Belum ada profil perangkat Android untuk QA, tidak ada emulator
  di laptop.
- Belum ada keputusan: aplikasi jalan di Android 9 sampai 15 atau
  minimal 10.

## 3. Fine-tuning model

### Target
Naikkan akurasi bersih dan tahan lapangan. Sekarang 0,7156 (uji
bersih) dan 0,5082 (ponsel iNaturalist). Target realistis: +5
poin bersih, +10 poin ponsel.

### Deliverable
- Skrip latih reproducible (`seed=42`, hidden=256, lr=0,001,
  epoch=300 sesuai `ml/train.py`).
- Laporan per spesies sebelum-sesudah dengan support per spesies
  (sekarang 3 sampai 8 klip, satu klip geser 12 poin).
- Seed tetap, `--resume` teruji, threshold per-spesies di-`sync`.
- Embedding memakai BirdNET 1024-dim beku (backbone jangan
  di-unfreeze dulu).

### Urutan kerja
1. Audit mutu data: cek sha256 lintas split (pernah ada leakage),
   saring ND (446/1370 klip ND sebelumnya), cek duplikat.
2. Tambah data lapangan nyata 30 sampai 50 menit audio sendiri,
   validasi sampel deteksinya lewat aplikasi.
3. Fine-tune dari bobot produksi (`ml/checkpoints/best_model.npz`),
   bukan dari nol. `--resume` saja, seed tetap.
4. Laporkan metrik per spesies, bukan satu angka global.
5. Bandingkan sebelum-sesudah pada tangga degradasi dan korpus
   lapangan nyata (Xeno-canto, iNaturalist, pengecoh).
6. Sinkronkan `thresholds.json` ke DB lewat `make sync-thresholds`.

### Celah
- `ml/augment_train.py` pernah bukti augmentasi memperburuk akurasi
  bersih (0,5862) karena overfit. Jangan ulang tanpa kontrol.
- Angka `confidences` belum dikalibrasi (kalibrasi hanya pada
  threshold, bukan probabilitas). Klaim "confidence terkalibrasi"
  di README tidak benar.
- Tidak ada few-shot untuk spesies langka (Prinia familiaris
  support 3).
- `ml/data/degraded` 12 GB dan `ml/data/audio` 7,6 GB. Sisa
  disk sekitar 17 GB. Bersihkan sebelum latih ulang.
- Latensi CPU 3,4 kali realtime (5,75 detik audio 19,4 detik).
  Belum diukur di HP kelas bawah atau AudioMoth.

## 4. Testing

### Target
Test hijau bukan bukti ownership, deployment, atau produksi. Target:
test hijau + probe runtime nyata untuk setiap kelas temuan.

### Deliverable
- `audit_probe.py`, `verify_features.py`, `security_check.py`,
  test API, test worker, test web lulus di database bersih.
- Probe authorization lintas akun dengan ranger baru, bersihkan
  setelahnya.
- Probe input batas (password 1 char, file teks ber ekstensi audio,
  batch 20, device nonaktif, ID lintas akun).
- CI merah karena database lokal lama berbeda dengan CI. Jalankan
  di database bersih tiap kali sebelum mengaku selesai.

### Urutan kerja
1. Jalankan ulang semua test di database bersih (CI = `gemahutan_cicheck`).
2. Probe `get_current_user` bukan bukti ownership. Cek source
   `app/deps.py` untuk filter `owner_id`/`uploaded_by` per endpoint.
3. Tambah test untuk: range audio HTTP 206, hapus object yatim,
  rate limit selain login, token revocation di Redis.
4. Uji worker tanpa demo data: `docker compose run --rm -T -v ...`.
5. Click-through tidak hanya klik: ambil status job dari API
  dan nyatakan lulus hanya kalau `done`.
6. `audit_probe.py` terulang pada viewport 390 dan 1440.

### Celah
- `/healthz` belum `/readyz` (cek DB, Redis, storage, migrasi,
  heartbeat worker).
- Tidak ada audit log perubahan peran, verifikasi, metadata, retry.
- Backup mengenkripsi DB tapi belum diuji restore object storage.
- MFA admin belum ada, refresh-token rotation belum, validasi
  magic bytes audio belum.
- Rate limit hanya di login, tidak di endpoint berat
  (`/spectrogram`, `/audio`).
- Email verification, forgot password, dependency audit (`npm audit`,
  `pip-audit`) belum dijalankan otomatis di CI.

## 5. Lokalisasi jarak (jawaban langsung)

### Cara sekarang
`ml/localization.py` punya fungsi `jarak_dari_selisih_level`:
- Input: level RMS jendela deteksi (dBFS), level referensi
  (dBFS), jarak referensi (m).
- Rumus: `jarak = jarak_ref * 10 ** ((level_ref - level_ukur) / 20)`.
- Worker (`apps/worker/worker.py:469`) panggil fungsi ini dengan
  `acuan_jarak` dari kolom `devices.reference_distance_m` dan
  `devices.reference_level_db`.

### Syarat agar `range_m` terisi
1. Rekaman multi-kanal (>= 2 mikrofon).
2. Perangkat punya `mic_spacing_m`, `reference_distance_m`,
   `reference_level_db`.
3. Worker mendapat acuan, isi kolom `detections.range_m`.

### Kenapa sekarang null
- Tidak ada perangkat dengan kolom acuan terisi (belum pernah
  dikalibrasi di lapangan).
- Rekaman yang ada di DB kebanyakan 1 kanal (audio yang diunduh
  ke demo mono, atau webm dari peramban).
- `bangun_sintetis` modul bisa menguji dengan sumber 1 sampai 100 m
  dan jarak acuan 10 m, tapi belum dipakai end-to-end.

### Yang harus dibangun
1. Kalibrasi perangkat: fitur UI bagi admin untuk masukkan
   `reference_distance_m`, `reference_level_db`, dan
   `mic_spacing_m` setelah pengukuran lapangan.
2. Prosedur kalibrasi: rekam spesies diketahui pada jarak 10 m
   dengan mikrofon array, hitung RMS jendela, simpan sebagai acuan.
3. Dataset audio multi-kanal nyata, bukan sintetis. Saat ini
   `bangun_sintetis` saja yang ada.
4. Validasi: ukur galat jarak pada 10, 20, 30, 50 m sumber
   sebenarnya dengan perangkat yang sudah dikalibrasi. Laporkan
   galat RMS dan MAE.
5. Antarmuka: tampilkan `range_m` di detail rekaman dengan
   indikator "kalibrasi" atau "perkiraan kasar".
6. Tanpa kalibrasi, kembalikan `null` seperti sekarang. Jangan
   tebak.

## 6. Urutan eksekusi (prioritas)

Minggu 1: pulihkan worktree web, audit `app/deps.py` ownership,
test database bersih.
Minggu 2: layer deteksi di peta, tampil `range_m` di detail
rekaman, kalibrasi perangkat v1 (UI saja, data sintetis).
Minggu 3: fine-tune dengan data lapangan sendiri (30 sampai 50
menit), audit mutu data, bandingkan sebelum-sesudah per spesies.
Minggu 4: scaffold Android Kotlin, rekam foreground, antrean lokal.
Minggu 5: Android background service + resume upload, audit
ekspor PDF, audit accessibilitas viewport 390.
Minggu 6: deployment publik dengan `ALLOW_REGISTRATION=false`,
ganti password demo, security headers, MFA admin opsional.
