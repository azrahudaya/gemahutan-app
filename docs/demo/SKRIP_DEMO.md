# Skrip demo GemaHutan

Untuk presentasi 10 menit (seleksi 22 Oktober), video presentasi, dan sesi tantangan juri. Semua yang
didemokan harus sudah berjalan di https://gemahutan.site pada hari H. Periksa daftar persiapan sehari
sebelumnya.

## Pembagian peran

| Orang | Tugas |
|---|---|
| Pembicara | Bercerita: masalah, solusi, bukti, tahapan |
| Operator | Memegang laptop dan ponsel; menjalankan langkah di bawah tanpa banyak bicara |

Panduan lomba mewajibkan pembagian operator dan pembicara. Tentukan siapa pegang apa dan latih minimal dua
kali dengan pengatur waktu.

## Persiapan (H-1)

- [ ] Tiga akun juri sudah diundang dan aktif: admin, peneliti, *ranger*. Sandi disimpan di pengelola sandi,
      bukan di slide.
- [ ] Satu lokasi pemantauan contoh sudah dibuat admin. Pakai nama dan koordinat sungguhan kawasan yang akan
      dijadikan contoh.
- [ ] Ponsel operator sudah masuk sebagai *ranger* di gemahutan.site, izin mikrofon sudah diberikan.
- [ ] Laptop sudah masuk sebagai peneliti di satu peramban dan admin di jendela penyamaran.
- [ ] Berkas contoh siap di laptop: `ml/demo_audio/xc-938488.mp3` (Merbah Cerukcuk) dan
      `ml/demo_audio/xc-46911.mp3` (Kirik-kirik Laut). Unggah satu berkas H-1 supaya hasilnya sudah ada kalau
      jaringan lambat.
- [ ] Surel peringatan spesies prioritas sudah pernah terkirim minimal sekali, dan tangkapannya ada di slide
      cadangan.
- [ ] Rencana cadangan:
  - stack lokal (`docker compose up -d`) sudah jalan di laptop;
  - video rekaman layar demo lengkap (≤3 menit) ada di desktop.

  Kalau internet ruangan mati, pindah ke salah satunya tanpa panik.

## Alur 10 menit

| Menit | Pembicara | Operator (layar) |
|---|---|---|
| 0:00–1:30 | Masalah: 1.834 spesies burung, 159 terancam (Burung Indonesia, 2026); perdagangan burung kicau; rekaman menumpuk dan tidak ada yang sempat mendengarkan | Slide masalah |
| 1:30–2:30 | Solusi: GemaHutan untuk petugas konservasi; tiga peran; lima tahap, sekarang Tahap 1 | Halaman depan, lalu `/tentang` bagian Tahapan |
| 2:30–4:00 | *Ranger* di lapangan: rekam dari ponsel tanpa memasang aplikasi | Ponsel (layar dicerminkan): Rekam → pilih lokasi → rekam 15 detik → unggah. Lalu Unggah di laptop dengan `xc-938488.mp3` |
| 4:00–5:00 | Hasil otomatis: BirdNET + model lokal 25 spesies, skor per spesies, spektrogram | Detail rekaman: pemutar, spektrogram, daftar deteksi |
| 5:00–6:00 | Peneliti memverifikasi: angka mutu jujur, deteksi = kandidat | Tandai Benar/Salah/Ragu, lalu ekspor CSV |
| 6:00–7:00 | Spesies prioritas dan kerahasiaan lokasi: peta burung langka adalah incaran pemburu | Admin: daftar spesies dengan lencana Prioritas; tunjukkan surel peringatan; bandingkan koordinat yang dilihat *ranger* (dibulatkan) dengan admin |
| 7:00–8:15 | Perkiraan lokasi: dasar Tahap 3, diuji dengan simulasi | `/simulasi`: taruh 3 alat virtual dan satu sumber, tekan Hitung, tunjukkan area perkiraan dan selisihnya |
| 8:15–9:00 | Dasbor dan laporan bulanan untuk balai | Dasbor, peta, laporan siap cetak |
| 9:00–10:00 | Bukti dan langkah berikutnya: SUS 77,0 (Good) dari 5 mahasiswa Kehutanan Unila; biaya USD 50 per bulan; Tahap 2 uji lapangan di satu kawasan mitra | Slide penutup |

Jangan menjelaskan kode atau arsitektur di 10 menit ini kecuali ditanya. Simpan untuk tanya jawab.

## Pertanyaan juri yang mungkin muncul

| Pertanyaan | Jawaban singkat (jujur) |
|---|---|
| Judulnya burung langka, tapi 25 spesies model kebanyakan burung umum? | Benar. 25 spesies dipilih karena datanya tersedia berlisensi terbuka, untuk membangun dan menguji alurnya. Spesies langka target kawasan masuk di Tahap 2 dari rekaman lapangan yang diverifikasi pakar. BirdNET global (6.522 spesies) sudah aktif untuk spesies di luar daftar |
| Seberapa akurat? | F1 makro 0,729 pada validasi silang per perekam; uji independen 0,756. Di rekaman ponsel turun, dan sebagian spesies pengecoh masih memicu deteksi palsu. Karena itu setiap deteksi diperlakukan sebagai kandidat yang diverifikasi peneliti. (Sesuaikan angka dengan Tabel 6 versi terakhir) |
| Bagaimana menghitung lokasi? | Selisih waktu tiba suara antar-mikrofon (GCC-PHAT) memberi arah tiap alat; arah dari beberapa alat dipotongkan (triangulasi). Simulasi: galat median sekitar 1 meter pada sinyal buatan tanpa gema. Itu batas atas; di hutan nyata lebih besar dan diukur di Tahap 2–3 |
| Kenapa tidak aplikasi Android? | Peramban ponsel sudah bisa merekam dan dipasang sebagai PWA. Tumpuan visi ada di alat perekam yang dipasang, bukan ponsel |
| Bagaimana kalau tidak ada sinyal di hutan? | Belum ada mode luring di Tahap 1. Rekaman dari alat perekam diunggah setelah petugas kembali ke jangkauan sinyal |
| Lisensi BirdNET? | CC BY-NC-SA 4.0, jadi GemaHutan hanya untuk tujuan non-komersial. Cocok untuk instansi konservasi |
| Keamanan data? | Akun dibuat admin lewat undangan, hak akses ditegakkan di API, lokasi spesies prioritas disamarkan untuk peran lain, dan cadangan basis data harian terenkripsi |
| Biaya operasional? | Satu server awan 4 vCPU, RAM 8 GB, tanpa GPU: USD 50 per bulan untuk satu kawasan |

## Tantangan juri (50% nilai babak)

Juri bisa meminta perubahan kecil langsung di perangkat lunak. Latih minimal tiga contoh ini sampai bisa
dikerjakan di laptop lokal dalam 10 menit:

1. **Mengubah ambang satu spesies.** Ambang ada di tabel `species` (`default_threshold`), disalin dari
   `ml/reports/thresholds.json` lewat `make sync-thresholds`. Tunjukkan efeknya di halaman Spesies.
2. **Menambah kolom atau teks di detail rekaman.** Berkas: `apps/web/src/app/(app)/recordings/[id]/page.tsx`.
   Data dari `GET /api/v1/recordings/{id}` di `apps/api/app/routers/recordings.py`.
3. **Menandai spesies baru sebagai prioritas.** Admin: halaman detail spesies, tombol prioritas
   (`PATCH /api/v1/species/{id}/prioritas`).
4. **Menjelaskan alur satu rekaman di kode:**
   - unggah: `routers/recordings.py`;
   - antrean: Redis/ARQ;
   - pemrosesan: `apps/worker/worker.py`;
   - mesin model: `ml/engines/cascade.py`;
   - lokalisasi: `ml/localization.py`.

Siapkan juga: cara menjalankan lokal (`cp .env.example .env && docker compose up -d`, lalu
`http://localhost:3001`) dan cara membuka kode sumber di GitHub.

## Video presentasi (maksimal 10 menit, 1920×1080, mendatar)

- **Pembuka wajib** (aturan panduan): logo USB 2026, logo Universitas Gunadarma, logo atau ikon GemaHutan,
  nama produk, nama tim, dan nama seluruh anggota.
- **Semua anggota harus tampil**, tidak harus bersamaan.
- **Isi:** alur 10 menit di atas, direkam dari layar (laptop 1920×1080, ponsel dicerminkan) dengan suara
  pembicara.
- **Judul YouTube:** `USB 2026 | Software Development | Kata Ajra Bisa Ngoding Walaupun Token Habis | GemaHutan`,
  status *Unlisted*, tautan tetap aktif sampai acara selesai.
