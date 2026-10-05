# Catatan Verifikasi Klaim

Setiap angka pada proposal diambil dari berkas di dalam repositori. Tabel ini
mencatat sumbernya supaya angka dapat ditelusuri ulang.

## Angka mutu model

| Klaim | Nilai | Sumber |
|---|---|---|
| Akurasi data uji | 0,7795 | `ml/reports/eval.md`, `ml/reports/metrics.json` |
| Akurasi validasi terbaik | 0,6528 | `ml/checkpoints/meta.json`, `ml/reports/eval.md` |
| Presisi makro, recall makro, F1 makro | 0,7306, 0,7396, 0,7194 | `ml/reports/metrics.json` |
| Pembagian data 959 latih, 193 validasi, 218 uji | sesuai | `ml/reports/eval.md`, `ml/data/splits.json` |
| Cakupan jalur A 6522 spesies | sesuai | keluaran `GET /api/v1/model/info` dari worker yang berjalan |
| Ambang per spesies 0,10 sampai 0,60 | sesuai | `ml/reports/thresholds.json` |

## Angka lapangan dan degradasi

| Klaim | Nilai | Sumber |
|---|---|---|
| Kontrol pengodean ulang | 0,6759 | `ml/reports/field_metrics.json`, `field_eval.md` |
| Angin, hujan ringan, kota | 0,6250, 0,6065, 0,5880 | sama |
| Jarak 30 m, hujan deras, jarak 100 m | 0,5622, 0,5370, 0,5194 | sama |
| Gabungan berat | 0,2817 | sama |
| Xeno-canto C sampai E | 0,6594 | sama |
| Rekaman ponsel iNaturalist | 0,5082 | sama |
| Deteksi palsu pada klip pengecoh | 0,6172 | sama |
| Eksperimen augmentasi | 0,5862 dan 0,5 sampai 2,8 poin | `ml/reports/field_experiments.md`, `field_metrics_aug*.json` |
| Penyaring deteksi lemah 65 menjadi 38 deteksi | sesuai | catatan sesi di `docs/arsip/PROGRESS.md` |

## Angka lokalisasi

| Klaim | Nilai | Sumber |
|---|---|---|
| Galat arah median 0,0 derajat pada SNR 30 sampai 5 dB | sesuai | keluaran `ml/validate_localization.py`, ringkasan di `docs/arsip/PROGRESS.md` |
| Galat maksimum 1,0 derajat pada SNR 0 dB | sesuai | sama |
| Galat median 0,5 derajat pada SNR -5 dB | sesuai | sama |
| Susunan bentang 1,2 m | galat median 0,5 derajat | sama |
| Triangulasi dua dan tiga perangkat | 14,4 m dan 27,2 m | sama |
| Kepekaan jangkauan terhadap taksiran level | 3 dB ke 14,1 m, 6 dB ke 20,0 m, 10 dB ke 31,6 m | sama |
| Uji klip demo empat kanal | azimuth 60,0 derajat, galat 0,00 derajat, keyakinan 0,58, jangkauan kosong | pengukuran 21 September 2026 memakai `ml/buat_klip_multikanal.py` dan endpoint deteksi |

## Angka kinerja dan pengujian

| Klaim | Nilai | Sumber |
|---|---|---|
| Audio 19,4 detik diproses 5,75 detik | sesuai | catatan sesi di `docs/arsip/PROGRESS.md` |
| Spektrogram pertama 0,269 detik dan berikutnya 0,049 detik | sesuai | `docs/arsip/PROGRESS.md`, header `x-spektrogram-cache` |
| Test API 57, test worker 25, test antarmuka 51 | sesuai | `docker compose exec api python -m pytest tests/ -q`, `make test-worker`, `npx vitest run` |
| 28 pemeriksaan fitur lulus | 28 dari 28 | keluaran `python3 ops/verify_features.py` |
| 6 pemeriksaan keamanan lulus | 6 dari 6 | keluaran `python3 ops/security_check.py` |
| Uji klik 24 langkah, 0 galat konsol | sesuai | keluaran `python3 ops/e2e_clickthrough.py` |
| Geser horizontal 0 piksel pada lebar 390 piksel | 0 | keluaran uji klik, bagian mobile |

## Klaim fitur yang perlu dicek ulang sebelum submit

1. Jumlah endpoint disebut 36 path pada versi ini. Angka itu dari `/openapi.json`;
   hitung ulang sesudah semua perubahan dibekukan.
2. Rekaman lapangan asli masih nol, sehingga bab Hasil tidak boleh menampilkan angka
   lapangan milik kami sendiri.
3. URL publik belum dipasang. Kalimat "dapat dijalankan pada platform umum" dijawab oleh
   pemasangan lokal, dan perlu diperbarui kalau URL publik sudah ada.
4. Halaman Laporan mencetak PDF lewat peramban. Kalau panitia meminta berkas PDF dari
   server, fitur itu belum ada dan harus dikerjakan lebih dulu.
5. Nama produk pada nama berkas wajib panitia belum ditetapkan bentuk bakunya. Gunakan
   "GemaHutan" pada nama berkas proposal dan presentasi.
