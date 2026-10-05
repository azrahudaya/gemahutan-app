> **Arsip, tidak berlaku lagi.** Dipindahkan ke `docs/arsip/` pada 3 Oktober 2026. Acuan yang
> berlaku: `docs/VISI_DAN_RUANG_LINGKUP.md`. Isi di bawah boleh dibaca untuk sejarah, tetapi
> jangan dijadikan dasar tugas.

# GemaHutan: Audit dan Rencana

Diperbarui: 21 September 2026
Status: Fase 2 selesai dikerjakan, siap diverifikasi

Dokumen ini menggantikan versi 14 September. Bagian yang dulu tercatat sebagai
kekurangan sekarang ditulis apa adanya: mana yang sudah selesai beserta buktinya,
mana yang masih kurang. Cara memeriksa ulang semuanya ada di bagian F.

## A. Keadaan hari ini

| Komponen | Status | Bukti atau catatan |
|---|---|---|
| Docker Compose 6 service | Jalan | api, worker, web, db, redis, minio sehat |
| Auth JWT plus pencabutan token | Jalan | logout mencabut access dan refresh token lewat daftar jti di Redis, diuji `ops/security_check.py` |
| Unggah audio dan unggah batch | Jalan | satu berkas dan sampai 20 berkas sekali kirim, hasil per berkas, diuji `ops/verify_features.py` |
| BirdNET zero-shot (jalur A) | Jalan | cakupan global, 6522 spesies, dibaca dari heartbeat worker |
| Classifier lokal (jalur B) | Jalan | 25 spesies Indonesia, ambang per spesies hasil kalibrasi |
| Indeks soundscape ACI, NDSI, ADI, BI | Jalan | scikit-maad, hasil tersimpan per rekaman |
| Progres dan tahap job | Jalan | 10 tahap dari antre sampai selesai, ditulis setelah tiap tahap, dibaca UI |
| Siaran status job (SSE) | Jalan | `/api/v1/jobs/stream`, token lewat query, jantung tiap 15 detik, polling 5 detik tetap jadi cadangan |
| Peta lokasi | Jalan | MapLibre plus ubin OpenStreetMap, penanda lokasi, penanda sudut arah, lingkaran jangkauan |
| Perangkat perekam | Jalan | CRUD admin dengan jumlah kanal, jarak antar mikrofon, dan hitungan rekaman |
| Akun dan peran | Jalan | tiga peran ditegakkan di API, kelola akun hanya admin |
| Lokalisasi arah dan jangkauan | Sebagian | kolom tersimpan di deteksi dan ditampilkan di peta, tetapi heartbeat worker belum melaporkan bahwa modul lokalisasi terpasang |
| PWA | Jalan | manifes, service worker, ikon 192, 512, dan maskable, terpasang di layout |
| Halaman Model dan Laporan | Jalan | `/model` dan `/laporan`, angka dibaca dari API saat halaman dibuka |
| Manual | Jalan | `/dokumentasi` dan `docs/MANUAL.md` |
| Ekspor data | Jalan | deteksi terverifikasi dan daftar rekaman, csv atau json |
| Verifikasi ahli | Jalan | benar, salah, ragu, hasilnya jadi bahan latih ulang |
| Test | Jalan | 57 fungsi test API, 25 fungsi test worker, 57 test vitest web (diperiksa ulang 21 September 2026) |
| CI | Jalan | lint, test API, test worker, test web, e2e terjadwal |
| Backup dan pemulihan | Jalan | `make backup` dan `ops/backup_selftest.sh`, delapan tabel cocok |

## B. Temuan audit lama dan keadaannya sekarang

| Temuan 14 September | Keadaan 21 September | Bukti |
|---|---|---|
| Landing page tidak ada, `/` hanya mengalihkan ke login | Sudah ada halaman publik | `apps/web/src/app/page.tsx` |
| Peta masih placeholder | Peta MapLibre dengan penanda arah dan lingkaran jangkauan | `apps/web/src/components/sites-map.tsx`, halaman `/sites` dan `/sites/{id}` |
| Waveform viewer belum ada | Sudah ada | `apps/web/src/components/waveform-player.tsx` |
| Data demo belum ada | Ada 8 klip Xeno-canto nyata lewat `make demo` | `ml/demo_audio/`, `ATTRIBUTION.csv` |
| Tombol verifikasi belum ada di UI | Sudah ada di halaman detail rekaman | `apps/web/src/app/(app)/recordings/[id]/page.tsx` |
| Nilai model info di footer undefined | Halaman `/model` membaca `/api/v1/model/info` | `apps/web/src/app/(app)/model/page.tsx` |
| Responsive mobile belum diperiksa | Sudah: 0 px luapan mendatar di 5 halaman, 0 kontrol di bawah 44 px | `ops/e2e_clickthrough.py` |
| Dark mode hardcoded tanpa toggle | Tetap gelap, dan itu keputusan yang ditulis: alat lapangan dipakai malam, tidak ada janji toggle | `DESIGN.md` |
| PWA belum disetup | Sudah: manifes, service worker, ikon, metadata | `/manifest.webmanifest`, `/sw.js`, `apps/web/src/app/manifest.ts` |
| Test coverage tipis | 57 fungsi test API, 25 worker, 57 vitest (diperiksa ulang 21 September 2026) | `apps/api/tests/`, `apps/worker/tests/`, `apps/web/src/**/*.test.ts` |
| Smoke test dari repo bersih belum dilakukan | Belum, dan masih jadi utang | lihat bagian D |
| Ekspor CSV dan PDF belum ada | CSV dan JSON ada, PDF belum | `/api/v1/exports/verified`, `/api/v1/exports/recordings` |
| Notifikasi realtime belum ada | SSE sudah ada, notifikasi browser belum | `/api/v1/jobs/stream` |
| Admin panel belum ada | Sudah ada halaman Pengguna, hanya admin | `/admin/users` |
| i18n lengkap bahasa Inggris belum ada | Belum, dan tidak menjanjikan | lihat bagian D |
| Audio player belum terintegrasi | Sudah terintegrasi di halaman detail rekaman | `waveform-player.tsx` |
| Confusion matrix belum divisualkan | Skrip evaluasi menghitungnya, gambar ringkas belum dibuat | `ml/evaluate.py` |

## C. Fase 2: yang masuk sejak audit lama

1. Skema dan migrasi. `jobs.progress` dan `jobs.stage`, `recordings.batch_id`,
   `detections.azimuth_deg`, `azimuth_confidence`, `range_m`, `localization_engine`,
   kolom geometri perangkat, dan `species.model_supported`.
2. Perangkat. CRUD admin, baca untuk semua peran yang login, hapus ditolak 409
   selama masih dipakai rekaman.
3. Akun. Daftar, ubah peran, dan hapus, semuanya hanya admin, dengan penolakan 409
   untuk diri sendiri dan untuk admin terakhir.
4. Unggah batch. Sampai 20 berkas sekali kirim, satu berkas gagal tidak membatalkan
   sisanya, plus daftar batch dan rincian per berkas.
5. Progres dan tahap job yang bergerak per tahap, bukan menunggu selesai.
6. Siaran status lewat SSE sebagai pelengkap polling.
7. Lokalisasi. Blok `localization` di `/api/v1/model/info`, kolom lokalisasi di
   respons deteksi, penanda arah dan lingkaran jangkauan di peta, dan catatan kenapa
   arah belum tersedia kalau datanya memang belum ada.
8. PWA. Manifes, service worker yang tidak meng-cache API, ikon sendiri, tema hijau
   hutan untuk bilah peramban, metadata di layout.
9. Manual. Halaman `/dokumentasi` dan `docs/MANUAL.md`.
10. Laporan siap cetak. Halaman `/laporan` dengan CSS print, semua angka dibaca dari
    API, tanpa angka yang ditulis tangan.
11. Kebersihan seed. `seed.py` idempoten: upsert berdasarkan kunci alami, menandai
    25 spesies model, menghapus spesies asing yang tidak dipakai deteksi, dan
    mencetak jumlah ditambah, diperbarui, dihapus, serta jumlah `model_supported`.
12. Verifikasi fitur. `ops/verify_features.py` memeriksa 28 butir lewat HTTP dan
    mencetak PASS atau GAGAL per butir.

## D. Yang belum ada

Ditulis apa adanya, dan tidak diklaim ada:

- Rekaman lapangan asli. Seluruh audio berasal dari Xeno-canto, korpus lapangan
  turunan, dan klip demo.
- Aplikasi Android dan CLI portable, masih rencana di bagian E.
- Mode offline. Service worker menyimpan aset statis, bukan data rekaman, jadi
  mengunggah dan menganalisis tetap butuh jaringan.
- Perhitungan lokalisasi belum dikonfirmasi berjalan di worker lewat heartbeat,
  jadi `/api/v1/model/info` masih menulis `terpasang_di_worker` false. Modul dan
  testnya ada, tetapi sampai heartbeat melaporkan sebaliknya, statusnya belum
  dipastikan.
- Jalur pemrosesan masih menyamakan audio ke satu kanal. Selama itu belum berubah,
  satu rekaman tidak akan pernah menghasilkan arah datang, sekalipun perangkatnya
  berkanal banyak.
- Verifikasi email, reset kata sandi, dan pemindaian berkas unggahan belum ada.
- Kuota unggahan harian belum ada.
- Ekspor PDF belum ada. Laporan siap cetak memakai cetak peramban.
- Antarmuka bahasa Inggris belum ada.
- Smoke test dari repo bersih belum dilakukan sekali jalan penuh.
- Alamat publik belum dipasang. Sebelum dipasang: pendaftaran akun wajib ditutup,
  kata sandi akun contoh wajib diganti, dan `ENVIRONMENT=production` wajib diset
  supaya `/docs` mati dan rahasia contoh ditolak.

## E. Rencana berikutnya

### Android dan perekam lapangan

Catatan 21 September 2026: pilihan teknologi ini ditinjau ulang di
`docs/RENCANA_PRODUK.md` bagian 1.2, yang merekomendasikan Kotlin native untuk
target Android saja dan Flutter hanya kalau benar-benar perlu iOS.

Pilihan tetap Flutter: satu basis kode untuk Android dan iOS, plugin rekam audio
matang, dan hasilnya bisa langsung mengunggah ke API yang sama.

| Fitur | Prioritas | Catatan |
|---|---|---|
| Masuk dan simpan token | P0 | API dan peran sudah siap |
| Rekam audio | P0 | Kirim sebagai webm atau wav, jalur unggah sudah menerima keduanya |
| Unggah dan antrean | P0 | Pakai `/api/v1/recordings/batch` supaya langsung dapat nomor batch |
| Riwayat dan status job | P0 | Baca progres dan tahap per rekaman |
| Hasil deteksi | P0 | Termasuk kolom lokalisasi kalau ada |
| Pilih lokasi dan perangkat | P1 | Perangkat berkanal banyak membuka jalan lokalisasi |
| Mode offline | P1 | Rekam tanpa jaringan, unggah saat ada sinyal |
| Rekam berkanal banyak | P1 | Ini yang benar-benar membuka arah datang di lapangan |
| Notifikasi selesai | P2 | Bisa memakai SSE atau kirim ulang saat aplikasi dibuka |

### CLI portable

Tujuan tetap sama: `git clone`, pasang, lalu analisis audio tanpa Docker. Perintah
yang direncanakan `gemahutan analyze berkas.wav`, dengan keluaran tabel, json, atau
csv, plus opsi indeks soundscape. Bagian yang bisa dipakai ulang sudah ada di
`ml/engines/` dan `ml/reports/`.

### Produksi

Urutan yang benar saat alamat publik dipasang: tutup pendaftaran akun, ganti kata
sandi akun contoh, set `ENVIRONMENT=production`, jalankan `ops/security_check.py`,
lalu `ops/verify_features.py`. Keduanya harus lulus sebelum URL dibagikan.

## F. Cara memeriksa ulang

```bash
make up                     # 6 service hidup
make migrate                # alembic upgrade head
make seed                   # idempoten, aman dijalankan berulang
make demo                   # 8 rekaman demo dari klip nyata
make test                   # test API
make test-worker            # test worker
python3 ops/verify_features.py   # 28 pemeriksaan fitur lewat HTTP
python3 ops/security_check.py    # 6 pemeriksaan keamanan
python3 ops/sync_thresholds.py   # ambang basis data dibandingkan laporan kalibrasi
cd apps/web && npx tsc --noEmit && npx vitest run
```

Hasil terakhir yang tercatat: `ops/verify_features.py` 28 dari 28 lulus, test vitest
57 lulus (periksa ulang 21 September 2026), `npx tsc --noEmit` bersih.

## G. Prioritas

1. Jalur audio berkanal banyak, karena tanpa itu lokalisasi tidak akan pernah jalan
   pada rekaman asli.
2. Smoke test dari repo bersih, supaya orang lain bisa mengulang semuanya.
3. Aplikasi Android dan CLI portable.
4. Kuota dan pemindaian unggahan, verifikasi email, reset kata sandi.
5. Antarmuka bahasa Inggris.
6. Gambar ringkas confusion matrix di laporan evaluasi.
