# Visi dan ruang lingkup GemaHutan

**Dokumen acuan utama.** Ditetapkan pemilik produk pada 3 Oktober 2026. Kalau dokumen lain,
tugas, atau kode bertentangan dengan dokumen ini, dokumen inilah yang berlaku. Fitur di luar
daftar "Dibangun" tidak ditambahkan tanpa persetujuan pemilik produk.

## 1. Visi

GemaHutan adalah ekosistem untuk **mendeteksi dan memperkirakan di mana burung langka berada**.
Alat perekam yang dipasang di hutan menangkap suara. Model AI mengklasifikasi spesiesnya. Arah dan
jarak dari beberapa alat yang mendengar suara yang sama dipakai untuk memperkirakan lokasinya.

"Memperkirakan lokasi" punya dua arti, dan keduanya menjadi tujuan:

1. **Area asal suara saat itu.** Beberapa alat yang jamnya tersinkron mendengar kicauan yang sama,
   lalu sistem menghitung area perkiraan (bukan titik pasti) dari arah dan jarak.
2. **Peta peluang keberadaan.** Dari riwayat deteksi berminggu-minggu, sistem menunjukkan di mana
   dan kapan sebuah spesies paling mungkin ditemukan.

Saat ini GemaHutan baru berada di **Tahap 1: perangkat lunak**. Alat perekam belum terpasang.

## 2. Pengguna

GemaHutan dibuat untuk **petugas konservasi**, bukan pengguna umum.

| Peran | Siapa | Yang dikerjakan di GemaHutan |
|---|---|---|
| Admin kawasan | Pengelola Balai Taman Nasional atau BKSDA | Membuat akun petugas, mengelola lokasi dan perangkat, menetapkan spesies prioritas, membaca laporan bulanan |
| Peneliti | Ahli burung, peneliti mitra | Memverifikasi deteksi (Benar, Salah, Ragu), mengekspor data terverifikasi, membaca detail teknis |
| Ranger | Polhut, petugas lapangan, relawan | Merekam atau mengunggah, melihat hasil rekamannya sendiri, memakai simulasi perkiraan lokasi |

Akun hanya dibuat oleh admin. Pendaftaran mandiri ditutup di produksi.

## 3. Tahapan pengembangan

| Tahap | Isi | Status |
|---|---|---|
| **1. Perangkat lunak** | Model klasifikasi 25 spesies burung Indonesia (BirdNET + classifier lokal), aplikasi web untuk tiga peran, verifikasi ahli, laporan, **simulasi perkiraan lokasi** dengan alat virtual | Berjalan, sebagian sudah jadi |
| **2. Uji lapangan** | Satu kawasan mitra, alat perekam terpasang, rekaman diverifikasi ahli, angka akurasi lapangan resmi | Rencana |
| **3. Jaringan alat** | Alat dengan jam tersinkron (GPS), perkiraan area asal suara dari data nyata, peringatan spesies langka | Rencana |
| **4. Peta peluang dan ancaman** | Peta peluang keberadaan dari riwayat deteksi, deteksi suara ancaman (gergaji mesin, tembakan, kendaraan) untuk patroli | Rencana |
| **5. Skala nasional** | Banyak kawasan dalam satu sistem dengan hak akses per kawasan, data terbuka dalam format standar (Darwin Core) | Rencana |

Jenis alat perekam belum diputuskan. GemaHutan dibuat **netral terhadap perangkat**: rekaman dari alat
apa pun bisa diproses, asalkan waktu rekam dan posisi alat (serta jumlah kanal dan jarak mikrofon
untuk perkiraan arah) tercatat.

Satwa selain burung (katak, owa, serangga) masuk setelah burung kuat, sebagai kelompok tersendiri
dengan data latih dan evaluasi lapangannya sendiri.

## 4. Dibangun di Tahap 1

Semua fitur berjalan di **aplikasi web** (peramban laptop dan HP, bisa dipasang sebagai PWA).

**Halaman depan publik**
- Penjelasan untuk instansi, tombol **Masuk** sebagai aksi utama.
- **Coba contoh**: satu unggahan tanpa akun untuk calon mitra. Akun tamu terisolasi, maksimal
  10 unggahan per 24 jam, dihapus otomatis setelah 24 jam, tidak masuk data kawasan.
- Dokumentasi publik di `/dokumentasi`.

**Aplikasi setelah login**

| Fitur | Admin | Peneliti | Ranger |
|---|---|---|---|
| Rekam dari peramban HP | ✓ | ✓ | ✓ |
| Unggah banyak berkas (jalur utama dari alat perekam) | ✓ | ✓ | ✓ |
| Hasil analisis rekaman (pemutar, spektrogram, daftar deteksi) | semua | semua | miliknya sendiri |
| Indeks soundscape (ACI, NDSI, ADI, BI) | di detail rekaman | di detail rekaman | tidak ditampilkan |
| Simulasi perkiraan lokasi (alat virtual di peta) | ✓ | ✓ | ✓ |
| Verifikasi deteksi | ✓ | ✓ | |
| Ekspor CSV/JSON data terverifikasi | ✓ | ✓ | |
| Dashboard, peta kawasan | ✓ | ✓ | |
| Laporan bulanan per kawasan (siap cetak) | ✓ | ✓ | |
| Halaman Model dan Perangkat | ✓ | ✓ | |
| Kelola akun, lokasi, perangkat, spesies prioritas | ✓ | | |

**Spesies prioritas dan kerahasiaan lokasi**
- Spesies prioritas ditandai otomatis dari daftar resmi (IUCN CR, EN, VU dan Permen LHK
  P.106/2018), dan admin bisa menambah spesies target kawasannya.
- Lokasi tepat deteksi spesies prioritas hanya terlihat oleh admin dan peneliti, termasuk di
  ekspor. Di luar itu lokasinya disamarkan. Alasannya: peta lokasi burung langka adalah
  informasi yang dicari pemburu.

**Peringatan**
- Email ke admin dan peneliti ketika spesies prioritas terdeteksi: nama spesies, lokasi, waktu,
  tautan untuk mendengar potongannya.

**Email aplikasi**
- Undangan akun, atur ulang sandi, dan peringatan dikirim lewat Gmail yang sama dengan notifikasi
  server (SMTP dengan App Password, kredensial hanya di server).

**Penyimpanan audio**
- Audio penuh disimpan 90 hari untuk verifikasi. Setelah itu hanya potongan di sekitar deteksi
  yang disimpan seterusnya.

## 5. Tidak dibangun (dan alasannya)

| Tidak dibangun | Alasan |
|---|---|
| Aplikasi Android native | Web di peramban HP sudah cukup untuk ranger; tumpuan visi ada di alat perekam yang dipasang, bukan HP |
| Data contoh di server produksi | Server produksi bersih, hanya data asli petugas. Lokasi dan perangkat hasil seed dihapus, daftar spesies tetap. Juri mengunggah datanya sendiri |
| Pendaftaran akun mandiri | Petugas dibuat admin kawasan |
| Fitur sosial, statistik kunjungan publik, gamifikasi | Tidak dipakai di lapangan |
| Multi-kawasan dalam satu server | Tahap 5. Untuk pilot cukup satu kawasan per server |

## 6. Keadaan sekarang dibanding target (per 3 Oktober 2026)

| Bagian | Sekarang | Target Tahap 1 |
|---|---|---|
| Situs publik | Halaman depan + Coba contoh + dokumentasi + tombol Masuk | Ditambah tombol Masuk |
| Aplikasi petugas | Dibuka. Login per peran: ranger ke `/rekam`, lain ke `/dashboard`. Pendaftaran mandiri dihapus, `/register` dialihkan ke `/login` | Dibuka dengan login per peran |
| Akun | Admin mengundang lewat `/admin/users` (`POST /users/undang`), petugas mengaktifkan lewat email (`/atur-sandi`). Email menunggu `/etc/gemahutan/notif.env` diisi (blok C MENUNGGU PEMILIK) | Admin membuat akun dari aplikasi, petugas menerima email undangan |
| Hak akses per peran | Ekspor, statistik, daftar perangkat, dan indeks soundscape hanya peneliti dan admin (403 untuk ranger). Menu web mengikuti peran | Ditambah: ekspor, dashboard, Model/Perangkat hanya admin dan peneliti, indeks soundscape disembunyikan untuk ranger |
| Tampilan aplikasi | Tema hijau daisyUI `gemahutan` di komponen bersama, navbar, dan dashboard | Tema hijau daisyUI yang sama (lihat `DESIGN.md`) |
| Simulasi perkiraan lokasi | Ada di `/simulasi`: alat virtual di peta, arah GCC-PHAT, area perkiraan dari triangulasi | Alat virtual di peta, area perkiraan dihitung dari arah dan jarak |
| Spesies prioritas, kerahasiaan lokasi, peringatan email | Belum ada | Dibangun |
| Laporan bulanan per kawasan | Laporan ringkasan umum | Laporan bulanan per kawasan |
| Penyimpanan audio 90 hari | Belum ada | Dibangun |
| Model | 25 spesies, mutu lapangan masih rendah (lihat `ml/reports/`) | Promosi v5 (lisensi bersih), lalu perbaikan mutu lewat data lapangan |

## 7. Dokumen terkait

- `README.md`: gambaran proyek dan cara menjalankan.
- `DESIGN.md`: arah tampilan.
- `docs/MANUAL.md`: cara memakai aplikasi per peran.
- `docs/DEPLOY.md`: deploy ke server produksi.
- `docs/DECISIONS.md`: catatan keputusan teknis.
- `docs/arsip/`: dokumen lama yang sudah tidak berlaku, disimpan untuk sejarah.
