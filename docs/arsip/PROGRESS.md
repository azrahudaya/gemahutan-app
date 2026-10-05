> **Arsip, tidak berlaku lagi.** Dipindahkan ke `docs/arsip/` pada 3 Oktober 2026. Acuan yang
> berlaku: `docs/VISI_DAN_RUANG_LINGKUP.md`. Isi di bawah boleh dibaca untuk sejarah, tetapi
> jangan dijadikan dasar tugas.

# GemaHutan -- Progress

## Fase 0 -- Bootstrap & Self-healing  ✅ DONE  (2026-09-14 02:16 WIB)
**Task:** F00-T01 ... F00-T09 (9/9 done)
**Commit:** d58613e ... aade403
**Yang jadi:** repo init, state.json, dirs, NEEDS_FROM_YOU.md, watchdog, cron, self-healing proof
**Yang belum:** -
**Bukti:** ops/logs/watchdog.log, docs/DECISIONS.md

## Fase 1 -- Skeleton + Docker Compose  ✅ DONE  (2026-09-14 02:25 WIB)
**Task:** F01-T01 ... F01-T06 (6/6 done)
**Commit:** 2c001f2
**Yang jadi:** API + Worker + Web + DB + Redis + MinIO, semua container healthy, /healthz 200
**Yang belum:** -

## Fase 2 -- DB + Migration + Seed  ✅ DONE  (2026-09-14 02:40 WIB)
**Task:** F02-T01 ... F02-T05 (5/5 done)
**Commit:** 3710142
**Yang jadi:** 8 tabel (PostGIS), Alembic migration, 30 species + 6 sites seeded, healthz real checks
**Yang belum:** -

## Fase 3 -- Auth  ✅ DONE  (2026-09-14 02:50 WIB)
**Task:** F03-T01 ... F03-T05 (5/5 done)
**Commit:** 8321663
**Yang jadi:** register/login/refresh/logout, JWT, /me protected, test hijau
**Yang belum:** -

## Fase 4 -- Upload + Storage + Queue  ✅ DONE  (2026-09-14 02:55 WIB)
**Task:** F04-T01 ... F04-T05 (5/5 done)
**Commit:** b8f2ce4
**Yang jadi:** upload audio ke MinIO, job masuk queue, presigned URL
**Yang belum:** -

## Fase 5 -- Riset & Pilih Model  ✅ DONE  (2026-09-14 03:10 WIB)
**Task:** F05-T01 ... F05-T05 (5/5 done)
**Commit:** d6c17e2
**Yang jadi:** BirdNET v2.4 terunduh & teruji, model-selection.md, InferenceEngine interface, /model/info
**Yang belum:** -

## Fase 6 -- Inference Pipeline + Worker  ✅ DONE  (2026-09-14 03:20 WIB)
**Task:** F06-T01 ... F06-T05 (5/5 done)
**Commit:** 6738b17
**Yang jadi:** Worker real BirdNET inference, detections/species/stats/sites/jobs endpoints
**Yang belum:** -
**Bukti:** worker log: "Recording 2 processing complete"

## Fase 7 -- Acoustic Indices + Spectrogram  ✅ DONE  (2026-09-14 03:25 WIB)
**Task:** F07-T01 ... F07-T04 (4/4 done)
**Commit:** 7f7d50e
**Yang jadi:** Spectrogram PNG endpoint, acoustic indices endpoint
**Yang belum:** scikit-maad indices null (perlu debug di worker)

## Fase 8 -- Akuisisi Dataset  ✅ DONE  (2026-09-14 03:40 WIB)
**Task:** F08-T01 ... F08-T05 (5/5 done)
**Commit:** 08dd6ce
**Yang jadi:** 1800 klip sintetis (30 species x 50 + 300 negatif), manifest.csv, splits.json
**Yang belum:** Dataset Xeno-canto nyata (butuh API key v3, lihat NEEDS_FROM_YOU.md)

## Fase 9 -- Training Track B  ✅ DONE  (2026-09-14 03:50 WIB)
**Task:** F09-T01 ... F09-T05 (5/5 done)
**Commit:** ac086ce
**Yang jadi:** Embedding extraction (256-dim), MLP 2-layer, --resume terbukti, EmbeddingClassifierEngine
**Yang belum:** few-shot untuk spesies langka (backlog)

## Fase 10 -- Evaluasi & Kalibrasi  ✅ DONE  (2026-09-14 03:55 WIB)
**Task:** F10
**Commit:** 652589e
**Yang jadi:** eval.md per-species metrics, threshold kalibrasi, metrics.json
**Masalah:** Dataset sintetis, angka tidak representatif. Perlu data XC nyata.
**Angka:** Test acc 0.39, Macro F1 0.27 (sintetis)

## Fase 11 -- Frontend  ✅ DONE  (diperbarui 2026-09-21)
**Status sebelumnya:** `IN_PROGRESS`, "sedang membangun 6 layar Next.js" (14 September).
**Keadaan sekarang:** halaman publik, dashboard, rekaman, spesies, lokasi, laporan,
model, dokumentasi, admin akun, dan PWA sudah jalan.
**Commit:** `9b5dee2`, dilanjutkan `a8b3393` dan `3aac745`.

## Fase 12 -- CI + Docs  ✅ DONE (parsial)  (2026-09-14 04:00 WIB)
**Commit:** 6f72e9d
**Yang jadi:** GitHub Actions CI, ARCHITECTURE.md, API.md, DEPLOY.md
**Yang belum:** Final README update, smoke test dari repo bersih

---

## Sesi 21 September 2026: rencana produk dan CI remote yang merah

**Rencana produk**
- `docs/RENCANA_PRODUK.md` ditulis setelah sesi pukul 15:38 terputus sebelum
  rencananya tersimpan. Isinya keputusan tiga lapisan (web control plane,
  Android field capture, edge agent), penguatan Fase 3 dalam tujuh butir,
  ringkasan prioritas audit 21 September, dan daftar persiapan.
- Angka status dikoreksi supaya cocok dengan hasil periksa ulang: test worker 24
  jadi 25, test vitest 51 jadi 57, dan baris Fase 11 di atas ditandai selesai
  karena halamannya sudah jalan sejak `9b5dee2`.

**CI remote merah empat commit berturut-turut, penyebabnya ditemukan**
- Run gagal mulai tip `a8b3393` (14:43 WIB) sampai `4f490dc`, semuanya di
  langkah `Run API tests`:
  `tests/test_phase2_users.py::test_daftar_pengguna_sesuai_kontrak` gagal dengan
  `assert None == 'Admin'`.
- Sebabnya `app/seed.py` membuat akun dasar tanpa mengisi kolom `name`,
  sedangkan test kontrak menuntut nama "Admin". Di database lokal test tetap
  lulus karena baris admin lama masih menyimpan nama, jadi kekurangan seed tidak
  terlihat selama ini. Assertion itu masuk bersama `a645bc7`, dan CI baru
  menjalankannya pada push berikutnya.
- Perbaikan ada di commit `4271669`. Buktinya, bukan klaim: database bersih
  dibuat, `alembic upgrade head` lalu `python -m app.seed`, dan
  `SELECT email, name, role FROM users` menghasilkan Admin dan Peneliti. Seluruh
  test API di database bersih 53 lulus 4 dilewati, sama persis dengan CI, dan
  run CI commit `4271669` hijau untuk kedua job (lint-and-test, build-images).
- Bug kedua dari jalur yang sama: `apps/worker/worker.py:57` memakai DSN fallback
  dengan kata sandi tersamarkan `***`, sisa dari berkas yang pernah ditulis ulang
  dari hasil pembacaan yang tersamarkan. Sekarang nilainya benar.
- Pelajaran yang ditulis: test yang hijau di database lokal yang sudah lama
  dipakai tidak membuktikan apa pun. Jalankan juga di database bersih, karena
  itulah keadaan CI.

## Backlog (40%)
- Dataset Xeno-canto nyata (butuh API key)
- Fine-tune penuh (unfreeze backbone)
- Few-shot UI untuk spesies langka
- Retraining otomatis dari verifikasi ahli
- App Android native
- RBAC penuh
- Notifikasi realtime (SSE)
- Export PDF
- Multi-tenant
- Integrasi konfigurasi AudioMoth
- Admin panel
- i18n lengkap

## Sesi Perbaikan 20 September 2026

Fokus: memperbaiki yang rusak dan membuat demo bisa dipercaya, bukan menambah fitur.

**Endpoint dan data**
- Fix GET /api/v1/sites 500 (bug cast TextClause), tambah GET /sites/{id} dan POST /sites, plus kolom location, elevation_m, description, notes lewat migrasi 9c1d2e3f4a5b.
- Fix spectrogram 500 jadi 404/415/422 yang jelas, dan hanya jalan kalau audionya ada di storage.
- Tambah GET /recordings/{id}/audio untuk waveform player (token boleh lewat query).
- Validasi upload: ekstensi dan ukuran 200 MB benar-benar ditegakkan, enqueue gagal tidak lagi ditelan diam-diam.
- healthz dan /model/info tidak lagi hardcode: status model dibaca dari heartbeat worker di Redis dan artefak yang ada di image.

**ML dan worker**
- Worker memuat CascadeEngine (BirdNET + classifier Track B) dari image, bukan cuma BirdNET. Diverifikasi dari heartbeat: `{"engine": "cascade", "track_b": true}`.
- Indeks soundscape akhirnya terhitung: audio didekode dengan librosa (maad.sound.load hanya menerima wav), ACI/NDSI/ADI/BI memakai API scikit-maad 1.5 yang benar.
- Tambah cron heartbeat dan sweep job nyangkut, plus resampy untuk klip 44,1 kHz.

**Data demo**
- 8 rekaman demo palsu (baris DB tanpa audio) dihapus. Ganti dengan 8 klip Xeno-canto asli yang ikut repo di ml/demo_audio (2,4 MB) plus ATTRIBUTION.csv.
- `make demo` mengunggah klip, membuat job, dan worker memprosesnya. 44 deteksi dan 9 rekaman berstatus done adalah hasil hitung nyata.

**Kualitas**
- Tests: 11 lulus (sebelumnya 13 gagal dari 15). Penyebabnya pool asyncpg dipakai lintas event loop.
- CI: ruff bersih dengan konfigurasi ruff.toml, step lint web, dan pemeriksaan konsistensi data demo.
- Frontend: em dash dihapus, kontras teks diperbaiki (biru teks dipisah dari biru tombol), 126 kelas warna lama yang tidak valid dibersihkan, halaman /species ditambahkan, status pipeline di header diambil dari heartbeat.
- LICENSE MIT ditambahkan (badge README sebelumnya menunjuk file yang tidak ada).

## Sesi P0 Fitur 20 September 2026 (lanjutan)

Enam item prioritas nol dari audit fitur.

1. Filter halaman Rekaman benar-benar menyaring. Sebelumnya UI mengirim `site_id`, `date`,
   `min_confidence`, `limit` sementara API memakai `site`, `from`, `to`, `min_conf`,
   `page_size`, jadi tidak ada satu pun filter yang bekerja. Sekarang terbukti: tanpa filter
   9 baris, pilih lokasi jadi 1 baris.
2. Paginasi hidup. Respons `/api/v1/recordings` sekarang menyertakan `total_pages`, dan
   kontrolnya muncul saat data lebih dari satu halaman.
3. Halaman detail spesies berisi data nyata: status IUCN, threshold, kode eBird, jumlah
   deteksi, plus tabel riwayat deteksi lewat endpoint baru `/api/v1/species/{id}/detections`.
4. Loop verifikasi ke model benar-benar jalan. Endpoint `/api/v1/exports/verified` plus
   `ml/data/from_verifications.py` yang memotong deteksi terverifikasi jadi klip latih,
   menggabungkannya ke manifest dan split train. Bukti: deteksi 116 (Accipiter badius)
   jadi klip ver-116.wav 4 detik 48 kHz, masuk ke split train, manifest naik ke 1371 baris.
5. Tombol proses ulang ada di halaman detail rekaman, memakai endpoint retry dan status job
   dari `/api/v1/jobs`. Terbukti: job rekaman 11 attempts naik ke 3, status done, deteksi
   dihitung ulang, verifikasi lama tetap tersimpan.
6. Halaman detail rekaman menyegarkan diri sendiri tiap 5 detik selama status masih antre
   atau diproses, jadi tidak perlu reload manual.

Tambahan: ekspor CSV daftar rekaman dan CSV deteksi terverifikasi, kolom status di tabel
rekaman, tombol unduh CSV, pesan kesalahan yang jelas untuk tanggal dan status yang salah,
serta 5 test baru (16 lulus).

## Temuan dan Perbaikan Jalur ML 20 September 2026

Saat menguji loop verifikasi ke model, ketemu tiga masalah nyata di jalur latih:

1. `make eval` rusak. evaluate.py melakukan `from ml.train import MLP` tanpa menambahkan
   root repo ke sys.path, jadi perintah dari Makefile selalu gagal ModuleNotFoundError.
2. Default hyperparameter tidak mereproduksi angka yang dilaporkan. Default train.py
   adalah 100 epoch, hidden 128, lr 0.01 dan hanya menghasilkan val_acc sekitar 0.46,
   sedangkan angka di laporan datang dari run 300 epoch, hidden 256, lr 0.001. Default
   sudah diselaraskan dengan run tersebut.
3. Tidak ada seed tetap, jadi hasil antar run berbeda. Terukur val_acc 0.57 sampai 0.65
   dengan konfigurasi identik. train.py sekarang menerima `--seed` dengan default 42,
   dan laporan menyebut seed yang dipakai.
4. Laporan evaluasi masih menyebut "dataset sintetis" padahal data yang dipakai 1370 klip
   Xeno-canto nyata. Deskripsi dataset sekarang dibaca dari manifest dan splits, jadi
   tidak bisa lagi berbeda dari kenyataan.

Setelah perbaikan, latih ulang penuh memberi: test accuracy 0.7156, val accuracy 0.6528,
macro F1 0.7194 pada 218 klip uji, 25 spesies target plus 1 kelas negatif. Angka itu bisa
direproduksi dengan `python train.py --epochs 300 --hidden 256 --lr 0.001 --seed 42`.

Eksperimen terpisah (`ml/experiment_verified_impact.py`) membandingkan dataset tanpa dan
dengan klip hasil verifikasi ahli: 0.5699 dan 0.6321 pada val accuracy. Selisihnya
didominasi variasi antar run, bukan efek satu klip, jadi kesimpulan yang jujur adalah
loop verifikasi sudah berfungsi secara teknis tetapi butuh puluhan klip terverifikasi
per spesies sebelum efeknya terukur.

## Ronde Keamanan 20 September 2026

Empat masalah nyata ditemukan saat memeriksa keamanan, semuanya sudah ditutup:

1. Tidak ada pembatas percobaan login. Lima belas percobaan gagal berturut-turut
   semuanya dijawab 401, jadi kata sandi bisa ditebak tanpa henti. Sekarang lima
   percobaan gagal per email dan alamat IP per menit, berikutnya 429 dengan
   Retry-After.
2. Logout tidak mematikan token. Token yang sudah logout masih dijawab 200 oleh
   /api/v1/me sampai kedaluwarsa 30 menit. Sekarang jti access dan refresh token
   dicatat di Redis sampai kedaluwarsa, dan /refresh menolak refresh token yang
   sudah dicabut.
3. Port Postgres, Redis, dan MinIO di docker-compose.yml terikat ke 0.0.0.0,
   sehingga laptop yang ikut Wi-Fi kampus membuka database dan kredensial default
   MinIO ke seluruh jaringan. Sekarang semua port dev terikat ke 127.0.0.1.
4. .env masih memakai JWT_SECRET=change-me-in-production, artinya siapa pun bisa
   memalsukan token kalau di-deploy apa adanya. Rahasia lokal sudah diganti nilai
   acak, dan aplikasi sekarang menolak start kalau ENVIRONMENT=production dengan
   rahasia contoh, kredensial MinIO default, atau CORS localhost.

Tambahan: /docs dan /openapi.json mati otomatis saat produksi, dan pesan galat
decoder audio serta storage tidak lagi membocorkan detail internal ke klien.

Bukti: tests/test_security.py (4 test baru) plus ops/security_check.py yang
menjalankan enam pemeriksaan terhadap stack hidup. Hasil terakhir 6/6 lulus,
tests 20 lulus, click-through console error 0 dan request gagal nyata 0.


## Sesi 21 September 2026: evaluasi kondisi lapangan

Angka kondisi lapangan sekarang terukur dan bisa dipertanggungjawabkan. Angka lama di
`ml/reports/field_eval.md` tidak sah dan sudah diganti.

1. Tiga bug di jalur evaluasi ditemukan dan diperbaiki. Folder kontrol tangga degradasi
   dulu bernama "bersih", jadi menimpa baris baseline di laporan, baseline tertulis
   0,3102 padahal 0,7156. Pelabelan tidak sejajar karena berkas sunyi dilewati di
   tengah daftar, sehingga jendela audio bisa dapat label milik berkas lain, jarak 100 m
   tertulis 0,0570 padahal 0,5194. Berkas m4a tidak bisa didekode librosa, jadi 44
   rekaman ponsel iNaturalist dilewati diam-diam dan angka kelompok itu hanya dari 69
   berkas. Sekarang ada fallback ffmpeg di skrip evaluasi, worker, dan endpoint
   spektrogram, dan laporan mencantumkan kolom berkas terbaca.
2. Angka sekarang, uji bersih 218 jendela, macro F1 di dalam tanda kurung: bersih 0,7156
   (0,7244), kontrol reencode 0,6759, angin 0,6250, hujan ringan 0,6065, kota 0,5880,
   hujan deras 0,5370, jarak 30 m 0,5622, jarak 100 m 0,5194, gabungan berat 0,2817.
   Korpus lapangan nyata: Xeno-canto kotor 0,6594, rekaman ponsel iNaturalist 0,5082,
   deteksi palsu pada kelompok pengecoh 0,6172.
3. Lisensi: 446 dari 1370 klip manifest berlisensi ND, dan 50 klip ND di korpus lapangan
   dibuang. Filter ND di `field_corpus.py` dulu hanya berlaku untuk iNaturalist, tidak
   untuk Xeno-canto, dan pencocokan penandanya ikut menolak "cc-by-nc".
4. Augmentasi simulasi diuji dan hasilnya negatif, lalu dilaporkan apa adanya. Melatih
   dari nol dengan 1951 klip simulasi menurunkan akurasi bersih tanpa ND ke 0,5862 dari
   0,7034, penyebabnya overfit. Fine-tune dari bobot produksi sedikit lebih baik di
   hampir semua kondisi simulasi, termasuk Xeno-canto kotor 0,6594 ke 0,6719, tetapi
   tidak pada rekaman ponsel asli, 0,5082 ke 0,5000. Selisihnya 0,5 sampai 2,8 poin,
   terlalu kecil untuk diklaim sebagai perbaikan. Model aplikasi tetap model produksi.
   Rincian di `ml/reports/field_experiments.md`.
5. Unggahan dari ponsel: `ALLOWED_EXTENSIONS` memuat m4a, ogg, dan aac tetapi
   `ALLOWED_TYPES` tidak, jadi berkas itu ditolak dengan pesan "tipe file tidak
   didukung", dan kalaupun lolos akan gagal di worker. Daftar MIME dan ekstensi
   sekarang diselaraskan, dan worker mengonversi format yang tidak didukung librosa
   ke wav sebelum inference.
6. Daftar spesies diselaraskan dengan label map model. Lima spesies yang dikenal
   classifier tetapi belum ada di seed ditambahkan, yaitu Lesser Coucal, Zitting
   Cisticola, Black Drongo, Brahminy Kite, dan Collared Kingfisher. Basis data 52
   spesies, selisih dengan label map 0.
7. Disk dan konteks build: cache build Docker 16 GB dibersihkan, sisa ruang naik dari
   17 GB ke 36 GB. `.dockerignore` dan `.gitignore` diperluas supaya korpus turunan
   (degraded, field, augmented) tidak ikut konteks build atau repo.

8. Harness click-through `ops/e2e_clickthrough.py` diperbaiki: navigasi dulu menunggu
   `networkidle`, padahal aplikasi polling status dan peta menarik ubin OpenStreetMap,
   jadi navigasi bisa menggantung sampai timeout 30 detik. Sekarang DOM yang ditunggu,
   dan request gagal dipisah antara aplikasi dan host luar. Hasil terakhir: login,
   dashboard angka nyata 9 rekaman 22 spesies 35 deteksi 8 lokasi, spektrogram 1097 px,
   verifikasi tersimpan, filter 9 baris jadi 1 baris, ekspor CSV terpicu, mobile
   overflow 0 px di 5 halaman, console error 0, request gagal ke aplikasi 0, ke ubin
   peta 5 (jaringan, bukan aplikasi).


## Sesi 21 September 2026 (lanjutan): peran, ubah dan hapus data, aksesibilitas, operasi

P0 dan P1 dari audit model dan aplikasi dikerjakan, semuanya dengan bukti terukur.

1. Ambang spesies disamakan. Sebelumnya 23 dari 25 spesies menampilkan angka berbeda
   di halaman Spesies dibanding yang dipakai pipeline. Sekarang `ops/sync_thresholds.py`
   melaporkan 0 selisih, dan `seed.py` membaca `ml/reports/thresholds.json` supaya tidak
   melenceng lagi setiap kali seed dijalankan.
2. Peran ditegakkan di API. Sebelumnya kolom role tidak pernah diperiksa: siapa pun yang
   login bisa memverifikasi deteksi, menambah lokasi, dan mengulang job. Sekarang
   verifikasi dan retry butuh peneliti atau admin, lokasi butuh admin, dan tombol yang
   pasti ditolak tidak ditampilkan di UI.
3. Ubah dan hapus data. Tambah PATCH dan DELETE rekaman serta PATCH dan DELETE lokasi.
   Menghapus rekaman ikut membuang deteksi, indeks, job, berkas audio, dan cache
   spektrogramnya. Lokasi yang masih dipakai rekaman ditolak 409. Endpoint jadi 31 dari
   27, dan sebelumnya tidak ada satu pun operasi ubah atau hapus.
4. Halaman Model. `/model/info` sebelumnya tidak dipakai UI mana pun. Sekarang ada
   halaman /model berisi dua jalur deteksi, ambang per spesies, dan batas yang sudah
   diukur: rekaman ponsel 0,5082 dan deteksi palsu pada kelompok pengecoh 0,6172.
5. Aksesibilitas. Kontras 0 pelanggaran di 8 halaman. Fokus keyboard pada tautan
   navigasi sebelumnya tidak terlihat (outline 3px none, 0 piksel berubah saat difokus);
   sekarang ring 2px rgb(76,125,255). Kontrol di bawah 44px turun dari 83 menjadi 0 pada
   lima halaman mobile. `prefers-reduced-motion` dihormati.
6. Dashboard akhirnya punya state galat. Sebelumnya API yang diblokir hanya menampilkan
   kartu kosong tanpa penjelasan.
7. Penyaring deteksi lemah di engine cascade: durasi minimal 1 detik, dan keyakinan di
   bawah 0,5 harus muncul di dua potongan berbeda. Terukur pada 8 klip demo: 65 deteksi
   menjadi 38, yang dibuang memang yang lemah (0,118 sampai 0,304) sementara yang kuat
   (0,942 dan 0,804) tetap.
8. Cache spektrogram: render pertama 0,269 detik, permintaan berikutnya 0,049 detik
   dengan header `x-spektrogram-cache: hit`. Sebelumnya selalu 0,29 detik tanpa cache.
9. Batas percobaan job 3 kali, dan percobaan manual mereset hitungannya.
10. Halaman daftar rekaman menyegarkan diri tiap 10 detik, bukan hanya halaman detail.
11. Test: API 30 lulus (sebelumnya 21, tanpa test peran atau hapus), worker 8 test baru,
    frontend 9 test vitest baru. Click-through sekarang 24 langkah dan memverifikasi job
    benar-benar selesai setelah analisis ulang.
12. Ops: `make backup` (dump database, salinan audio, manifest) sudah diuji pulih lewat
    `ops/backup_selftest.sh`, delapan tabel cocok. `ops/RESTORE.md` memuat prosedurnya.
    CI menambah langkah test worker dan test web; e2e jadi workflow terjadwal.

Bug yang ketemu saat verifikasi: worker sempat memanggil `await` pada session yang
sinkron, sehingga setiap job baru gagal diproses dan rekaman tertinggal di status
processing. Sudah diperbaiki dan diuji: setelah perbaikan, retry rekaman 11 selesai
dalam 6 detik dengan 6 deteksi. Click-through sekarang menguji hal ini, jadi kegagalan
sejenis tidak lagi lolos diam-diam.

Data demo dirapikan: 5 rekaman sisa uji dihapus lewat endpoint hapus yang baru, dan 258
akun hasil pengujian dibersihkan. Sisa 9 rekaman demo dan 28 akun.


## Sesi 21 September 2026: prototipe lokalisasi sumber suara

Menanggapi permintaan memprediksi asal suara dan menampilkannya sebagai radius.

Yang dibangun:

- `ml/localization.py`: estimasi arah datang lewat GCC-PHAT antar pasangan kanal,
  pencarian azimuth 0,5 derajat, ukuran keyakinan dari arah alternatif, triangulasi
  beberapa perangkat, perkiraan jarak dari penyusutan amplitudo, dan pembangkit
  rekaman buatan untuk pengujian.
- `ml/validate_localization.py`: pengukuran pada rekaman buatan dengan arah dan
  jarak yang diketahui, ditutup ringkasan LULUS atau GAGAL.
- `docs/proposal/figures/fig09_lokalisasi.png`: ilustrasi dua mode tampilan.

Angka hasil pengukuran, array empat mikrofon bentang 0,5 m, sumber 25 m:

- galat arah median 0,0 derajat pada SNR 30 sampai 5 dB, keyakinan 0,97
- SNR 0 dB: median 0,0 derajat, maksimum 1,0 derajat
- SNR -5 dB: median 0,5 derajat, maksimum 3,5 derajat, keyakinan 0,94
- array bentang 1,2 m: median 0,5 derajat, maksimum 2,0 derajat pada SNR 20 sampai 0 dB
- triangulasi dua perangkat terpisah 300 m, galat arah 3 derajat: median meleset
  14,4 m, terburuk 56,0 m
- triangulasi tiga perangkat: median 14,4 m, terburuk 27,2 m

Batas yang harus disebut apa adanya:

- satu mikrofon tidak bisa menentukan arah sama sekali, yang bisa ditampilkan
  hanya lingkaran perkiraan jangkauan deteksi
- jarak dari amplitudo sangat sensitif: salah taksir level sumber 6 dB sudah
  menggeser hasil dua kali lipat (10 m terbaca 20 m)
- rekaman buatan belum memuat gema, pantulan, dan kicauan bertumpuk seperti
  subuh di hutan, jadi angka di atas adalah batas atas mutu
- beberapa perangkat butuh jam yang tersinkron; tanpa itu selisih waktu tiba
  antar perangkat tidak sah
- panggilan pita sempit membuat korelasi silang punya banyak puncak

Yang belum dikerjakan di aplikasi: jalur pemrosesan masih memaksa mono
(`ffmpeg -ac 1` dan `librosa.load(mono=True)`), tabel `devices` baru berisi nama,
jenis, dan lokasi, dan belum ada kolom arah atau jangkauan pada tabel deteksi.
