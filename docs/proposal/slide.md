# Presentasi USB 2026 (10 halaman)

Setiap halaman ditulis padat karena batas lomba maksimal 10 halaman. Angka yang
ditampilkan semuanya berasal dari bab Hasil dan Pembahasan proposal.

## Halaman 1: Sampul

- GemaHutan: Pemantauan Biodiversitas Hutan Indonesia Berbasis Bioakustik
- Lomba Software Development, USB 2026, Universitas Gunadarma
- TIM GEMAHUTAN
- Artya Epriliani, NPM 10124205 (ketua)
- Azra Hudaya, NPM 50423244
- Logo Universitas Gunadarma dan ikon aplikasi

## Halaman 2: Masalah

- Survei burung manual mahal: butuh pengamat ahli, perjalanan jauh, dan waktu berjam-jam
- Akibatnya banyak kawasan dipantau sekali setahun atau hanya saat ada laporan kerusakan
- Satu perekam dapat mengumpulkan puluhan jam audio, tetapi menyaringnya manual sama beratnya
- Model akustik yang tersedia umum: satu ambang untuk semua spesies, tanpa jejak pemeriksaan ahli

## Halaman 3: Solusi

- Alur lengkap dari unggahan sampai laporan di satu aplikasi web
- Dua jalur deteksi: penjaring 6522 spesies dan penilai khusus 25 spesies Indonesia
- Ambang keyakinan dikalibrasi per spesies
- Verifikasi peneliti yang menutup loop ke data latih
- Arah datang suara untuk menunjukkan ke arah mana pemeriksaan visual perlu dilakukan

## Halaman 4: Cara kerja

- Unggah berkas atau rekam langsung dari peramban, termasuk unggah batch 20 berkas
- Antrean Redis, worker menjalankan kedua jalur model, koordinat lokasi menyaring daftar spesies
- Deteksi, indeks akustik lanskap, dan spektrogram tersimpan bersama rekamannya
- Tahap dan persen kemajuan disiarkan ke antarmuka tanpa memuat ulang halaman

## Halaman 5: Mutu model

- Akurasi data uji 0,5512, F1 makro 0,5239, validasi terbaik 0,5433
- Data Xeno-canto Indonesia, 8.356 klip tanpa lisensi ND (446 ND disaring dari 1370 mentah)
- Pembagian per rekaman: 670 latih, 127 validasi, 127 uji
- Temperature scaling T=0,6972 menurunkan NLL val 15,01 persen dan ECE 0,176 ke 0,071
- Support per spesies hanya 3 sampai 8 klip, jadi angka per spesies selalu disebut bersama support
- Ambang per spesies 0,10 sampai 0,60

## Halaman 6: Uji kondisi lapangan

- Tangga degradasi delapan tingkat, gangguan dibangkitkan menurut target rasio sinyal terhadap derau
- Kontrol pengodean ulang 0,6759, angin 0,6250, hujan ringan 0,6065, kota 0,5880
- Jarak 30 m 0,5622, hujan deras 0,5370, jarak 100 m 0,5194, gabungan berat 0,2817
- Rekaman ponsel asli dari arsip publik 0,5082, sekitar 21 poin di bawah klip bersih
- Deteksi palsu pada klip pengecoh 0,6172

## Halaman 7: Eksperimen yang gagal, dan itu dilaporkan

- Melatih dari nol dengan 1951 klip simulasi menurunkan akurasi bersih ke 0,5862 karena overfit
- Fine-tune hanya menambah 0,5 sampai 2,8 poin pada kondisi simulasi
- Pada rekaman ponsel asli, fine-tune tidak menambah apa pun
- Keputusan: model produksi tetap dipakai, dan angka ini ditampilkan di halaman Model

## Halaman 8: Arah datang suara

- GCC-PHAT antar pasangan kanal, sudut dicari pada langkah 0,5 derajat
- Galat arah median 0,0 derajat pada SNR 30 sampai 5 dB, keyakinan 0,97
- Susunan segaris tidak memisahkan 60 derajat dari 300 derajat, dan itu dilaporkan sebagai arah kembar
- Triangulasi tiga perangkat meleset median 14,4 m
- Jangkauan hanya diisi kalau perangkat dikalibrasi, karena taksiran level 6 dB menggeser hasil dua kali lipat

## Halaman 9: Bukti aplikasi berjalan

- Simulasi dan prakiraan saja tidak cukup, jadi setiap klaim diukur pada sistem yang berjalan
- 57 test API, 25 test worker, 51 test antarmuka
- 28 pemeriksaan fitur berbasis HTTP, 6 pemeriksaan keamanan
- Uji klik 24 langkah dengan 0 galat konsol dan 0 geser horizontal pada lebar 390 piksel
- Spektrogram pertama 0,269 detik, berikutnya 0,049 detik karena cache

## Halaman 10: Manfaat dan rencana

- Pengelola kawasan memperoleh riwayat kejadian spesies per lokasi beserta rekaman aslinya
- Peneliti memperoleh data berlabel dari hasil verifikasi untuk melatih model berikutnya
- Rencana lanjutan: rekaman lapangan sendiri, URL publik dengan pendaftaran ditutup, penambahan spesies
- Batas yang diakui: belum ada rekaman lapangan sendiri dan angka lokalisasi masih batas atas
