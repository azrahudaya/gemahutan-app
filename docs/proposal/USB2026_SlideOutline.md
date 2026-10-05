# Outline Presentasi USB 2026 (10 Slide)

> **Panduan render.** Berkas ini adalah sumber naskah untuk PPT/PPTX dengan nama
> `Presentasi_SoftwareDevelopment_TimGemaHutan_GemaHutan.pptx`. Ukuran maksimal
> 100 MB. Tiap slide memuat judul besar di atas dan daftar poin di bawah. Angka
> yang ditampilkan berasal dari `docs/proposal/USB2026_Proposal.md` bab 10.

## Slide 1. Sampul

**Konten visual:**
- Logo Universitas Gunadarma (pojok kiri atas).
- Logo USB 2026 (pojok kanan atas).
- Logo atau ikon aplikasi GemaHutan (tengah atas).
- Judul besar: **GemaHutan: Pemantauan Satwa Hutan berbasis Bioakustik dengan Cascade Classifier 26 Spesies Indonesia**.
- Baris lomba: Software Development, USB 2026, Universitas Gunadarma, 2026.
- Nama tim: TIM GEMAHUTAN.
- Tabel anggota:

| Nama | NPM | Peran |
|---|---|---|
| Artya Epriliani | 10124205 | Ketua |
| Azra Hudaya | 50423244 | Anggota |

## Slide 2. Masalah (3 kalimat kuat)

- Survei konvensional mahal: butuh pengamat ahli, perjalanan jauh, dan waktu berjam-jam untuk satu titik pantau.
- Kamera jebak gagal menangkap satwa vokal yang tidak pernah muncul di depan lensa, sehingga banyak spesies target tidak terdata.
- Model global yang tersedia memakai satu ambang untuk semua spesies tanpa jejak verifikasi ahli, sehingga hasilnya tidak konsisten untuk spesies lokal.

## Slide 3. Solusi GemaHutan (diagram arsitektur singkat)

- Aplikasi web end-to-end: unggah, proses, verifikasi, ekspor.
- Dua jalur deteksi komplementer: penjaring BirdNET 6.522 spesies global dan penilai cascade khusus 25 spesies Indonesia dengan ambang per spesies.
- Tiga persona: ranger (unggah), peneliti (verifikasi), admin (kelola).
- Tiga platform yang bertemu di API: web, Android (opsional), package Python `pip install gemahutan-ml` (rencana).
- Lima layanan di Docker Compose: api, worker, db, redis, minio.

Diagram: kotak alur dengan panah (visual, bukan teks panah) dari klien ke api, api ke worker via redis, worker ke minio, dan worker ke db.

## Slide 4. Alur kerja (unggah, proses, verifikasi, ekspor)

- Unggah: satu berkas atau batch sampai 20, dengan pemilihan lokasi dan perangkat.
- Antrean: Redis menerima job, worker mengambil dengan heartbeat.
- Proses: dekode, BirdNET, klasifikasi cascade, lokalisasi, indeks akustik, spektrogram.
- Verifikasi: peneliti memberi label benar, salah, atau ragu; hasil sebagai bahan latih.
- Ekspor: CSV rekaman dan deteksi terverifikasi, halaman laporan siap cetak.

## Slide 5. Teknologi (stack dengan badge)

Badge di awal slide:

`FastAPI` `Next.js 15` `PostgreSQL 16` `PostGIS 3.4` `Redis 7` `MinIO` `BirdNET 2.4` `scikit-maad` `TypeScript` `Tailwind` `Docker Compose`

Pemetaan singkat:

- API: FastAPI + SQLAlchemy async + Pydantic v2.
- Antarmuka: Next.js 15 + TypeScript + Tailwind CSS + TanStack Query.
- Peta: MapLibre GL dengan ubin raster OpenStreetMap.
- Model: BirdNET-Analyzer 2.4 (Jalur A) dan MLP numpy dua lapis (Jalur B).
- Antrean: Redis 7 + arq.
- Penyimpanan: MinIO dengan antarmuka S3.

## Slide 6. Hasil Model (tabel per spesies dengan support)

Tabel ringkas mutu keseluruhan:

| Metrik | Nilai | n |
|---|---|---|
| Akurasi uji | 0,7795 | 128 klip |
| Presisi makro | 0,7306 | 128 klip |
| Recall makro | 0,7396 | 128 klip |
| F1 makro | 0,7194 | 128 klip |

Dataset bersih tanpa lisensi ND: 8.356 klip, 26 kelas, tiap spesies minimal 5 klip. Pembagian per rekaman: 677 latih, 119 validasi, 128 uji. Support uji per spesies hanya 3 sampai 8 klip, jadi satu klip menggeser metrik 12 sampai 33 poin. Angka per spesies selalu disebut bersama support.

## Slide 7. Lokalisasi (arah dan jarak)

- GCC-PHAT antar pasangan kanal, langkah 0,5 derajat, geometri dari `devices`.
- Susunan segaris tidak memisahkan 60 derajat dari 300 derajat; dilaporkan sebagai `azimuth_kembar_deg`.
- Galat arah median 0,0 derajat pada SNR 30 sampai 5 dB.
- Triangulasi tiga perangkat meleset median 14,4 m.
- Jangkauan hanya diisi bila perangkat dikalibrasi (salah taksir level 6 dB sudah menggeser dua kali lipat).
- Foto: spektrogram dari `figures/fig09_lokalisasi.png` atau tangkapan layar `screenshots/10_detail_lokasi.png`.

## Slide 8. Dampak (lokasi prioritas, ranger workflow, efisiensi)

- Lokasi prioritas: peta dengan kerucut arah datang dan lingkaran jarak dari deteksi, sehingga ranger tahu ke arah mana harus bergerak.
- Ranger workflow: pilih lokasi, rekam dari HP, unggah, tunggu proses, verifikasi sederhana pada deteksi yang menarik.
- Efisiensi: 57 test API, 25 test worker, 57 test antarmuka, 28 pemeriksaan fitur, 6 pemeriksaan keamanan, semua lulus.
- Audio 19,4 detik diproses 5,75 detik pada CPU, sekitar 1,0 kali (belum diukur ulang) realtime.
- Spektrogram pertama 0,269 detik, berikutnya 0,049 detik karena cache.

## Slide 9. Rencana Lanjutan

- Aplikasi Android opsional: capture lapangan dengan antrean offline dan resume upload, dibangun setelah web stabil.
- Package Python `pip install gemahutan-ml`: latih dan evaluasi model lokal tanpa setup repo lengkap.
- Korpus lapangan: kumpulkan 30 sampai 50 menit rekaman sendiri, validasi lewat fitur verifikasi.
- Perluas spesies target di luar 25 spesies dengan hasil verifikasi lapangan.
- URL publik dengan pendaftaran ditutup dan kata sandi contoh diganti.

## Slide 10. Tim dan Penutup

- Tabel tim sama dengan slide 1.
- Ajakan: "GemaHutan, biosonar untuk hutan Indonesia."
- Kontak demo: `http://localhost:3001` pada mesin lokal.
- Terima kasih.
- Logo Universitas Gunadarma di tengah bawah.