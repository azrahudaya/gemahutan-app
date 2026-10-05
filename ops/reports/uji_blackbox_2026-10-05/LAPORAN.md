# Uji black-box GemaHutan, 5 Oktober 2026

**Lingkungan:**
- Stack lokal Docker dengan kode yang sama dengan produksi (commit `4041904` plus perbaikan W-32 dan W-35).
- Chromium lewat Playwright di layar ponsel 390 px dan desktop 1366 px.
- Mikrofon tiruan Chromium untuk uji rekam.
- Akun uji per peran (admin, peneliti, *ranger*).

**Pemeriksaan publik** dijalankan langsung ke https://gemahutan.site.

| Kode | Skenario | Hasil | Bukti |
|---|---|---|---|
| KF-01 | Admin mengundang akun; petugas membuat sandi lalu masuk | Lulus (surel dicatat ke log karena SMTP lokal kosong) | `kf01_undang.png`, `kf01_aktivasi.png` |
| KF-03 | *Ranger* rekam 30 detik di ponsel dan unggah 5 berkas | Sebagian: unggah 5 berkas lulus; rekaman Chrome ditolak "File tidak memiliki stream audio yang valid" (WebM tanpa durasi), lihat W-34 | `kf03_rekam_hp.png`, `kf03_unggah_5.png` |
| KF-04, 05 | Status otomatis sampai selesai; deteksi dan skor tampil | Lulus | `kf05_hasil_hp.png` |
| KF-06 | *Ranger* membuka rekaman akun lain | Lulus (404) | `kf06_rekaman_lain.png` |
| KF-08, 09 | Verifikasi dan ekspor CSV; *ranger* tidak bisa ekspor | Sebagian: verifikasi dan CSV lulus, API menolak *ranger* 403, tombol masih tampil (W-09) | `kf08_verifikasi.png`, `kf09_ekspor.csv`, `kf09_ranger_daftar.png` |
| KF-10 | Spesies prioritas: peringatan; lokasi tepat tidak terbuka bagi *ranger* | Lulus: Elang Bondol terdeteksi, peringatan dipicu (tidak terkirim karena SMTP kosong), *ranger* tidak menerima koordinat | `kf10_log_worker.txt` |
| KF-11 | Simulasi tiga alat memuat sumber | Lulus (galat 1,0 m, radius area 6,0 m) | `kf11_simulasi.png` |
| KF-07 | Laporan bulanan dicetak ke PDF | Belum: masih laporan ringkas (blok I) | `kf07_laporan.png`, `kf07_laporan.pdf` |

**Temuan kritis di produksi (pemeriksaan publik):**
- Peramban di gemahutan.site memanggil API ke `http://localhost:8000` dan diblokir CSP, sehingga Coba contoh
  dan login rusak (W-35, sudah diperbaiki di kode, menunggu deploy).
- Akses tanpa token ke `/api/v1/recordings`, `/exports/verified`, `/stats/overview`, dan `/users` dijawab 401
  (lulus).
- `/register` dialihkan ke `/login` (lulus).

Uji ulang dijadwalkan setelah W-34, W-35, W-09, dan blok I ter-deploy.

## Uji ulang (5 Oktober sore, folder `ulang/`)

**Lingkungan:**
- Image `api`, `worker`, dan `web` dibangun ulang dari commit `88563a6`.
- Ditambah perbaikan peninjau W-36 (tipe MIME berparameter) dan W-37 (pesan login salah).

| Kode | Hasil | Catatan |
|---|---|---|
| Login salah | Lulus | Pesan "Email atau kata sandi salah." tampil (sebelumnya halaman dimuat ulang tanpa pesan) |
| KF-01 | Lulus | |
| KF-03 | Lulus | Rekaman 30 detik tersimpan dan selesai diproses; 5 berkas terunggah. Sebelum W-36 ditolak 400 `audio/webm;codecs=opus` |
| KF-04, 05 | Lulus | |
| KF-06 | Lulus | |
| KF-08, 09 | Lulus | Tombol Unduh CSV tidak lagi tampil untuk *ranger* (W-09) |
| KF-10 | Lulus | Rekaman 761, Elang Bondol skor 0,998; peringatan dipicu (log worker: SMTP lokal kosong); *ranger* tidak menerima koordinat |
| KF-11 | Lulus | Galat 1,0 m, radius 6,0 m |
| KF-07 | Belum | Masih "Laporan Ringkas"; menunggu blok I |

**Produksi (peramban, setelah deploy W-35):**
- Coba contoh: tombol aktif, permintaan API menuju `https://gemahutan.site/api/...`, tanpa galat CSP.
- Hasil "2 spesies terdeteksi" (Merbah Cerukcuk 99,7%) tampil (`ulang_prod_coba_contoh.png`).
- Login sandi salah di produksi masih tanpa pesan, sampai W-37 ter-deploy.
- Rekam Chrome di produksi belum bisa diuji tanpa akun; menunggu deploy W-36.
