# Periksa Berkas Submit USB 2026 (kategori Software Development)

Daftar ini untuk dipakai sebelum mengunggah berkas ke panitia. Statusnya diisi
berdasarkan keadaan repo hari ini, bukan rencana. Kalau ragu, jalankan perintah
pada kolom cara cek.

## 1. Berkas wajib dan statusnya

| Berkas | Senjata wajib | Status | Cara cek |
|---|---|---|---|
| Proposal PDF | Maks 20 halaman, A4, spasi 1,5, font 12 Times New Roman, maks 50 MB | Ada: `docs/Proposal_SoftwareDevelopment_KataAjraBisaNgodingWalaupunTokenHabis_GemaHutan.pdf` | `ls docs/*.pdf` |
| Presentasi PPT | Maks 10 halaman, maks 100 MB, cover memuat anggota, nama produk, nama tim | Belum | - |
| Video presentasi | Maks 10 menit, minimal 1920x1080 landscape, YouTube unlisted, tautan tetap aktif | Belum | - |
| Surat pernyataan orisinalitas | Bermaterai, ditandatangani ketua tim, format LAMPIRAN 2 panduan | Draf ada (`docs/surat-pernyataan-usb.docx`), belum bermaterai dan ditandatangani | - |
| Software berbasis web | URL publik plus berkas lokal dan database | https://gemahutan.site hidup (VPS 4 vCPU, 7,7 GB, dengan worker). Aplikasi petugas masih dikunci, target dibuka dengan login per peran sebelum 9 Oktober | `curl -sI https://gemahutan.site` |
| Poster | Disebut pada tahap pengumpulan revisi, bukan pada daftar syarat berkas | Belum | - |

Nama berkas proposal wajib: `Proposal_SoftwareDevelopment_NamaTim_NamaProduk.pdf`.
Nama berkas presentasi wajib: `Presentasi_SoftwareDevelopment_NamaTim_NamaProduk.ppt`
atau `.pptx`. Judul video YouTube wajib mengikuti pola
`USB 2026 | Software Development | Nama Tim | Nama Produk`.

Cover proposal memakai LAMPIRAN 1 panduan: JUDUL, JENIS LOMBA, DISUSUN OLEH: NAMA TIM,
nama dan NPM tiap anggota, UNIVERSITAS GUNADARMA 2026.

## 2. Aset yang sudah siap di dalam repo

- Visi, tahapan, dan ruang lingkup: `docs/VISI_DAN_RUANG_LINGKUP.md`. Proposal, PPT, dan
  video wajib memakai tahapan di dokumen itu (Tahap 1 perangkat lunak, Tahap 2 sampai 5 rencana).
- Narasi dan angka: `docs/proposal/` (draft), `docs/MANUAL.md`, `README.md`.
- Grafik 11 berkas di `docs/proposal/figures/`. Untuk tangga degradasi pakai
  `fig08_degradasi_audio.png`, varian `_aug` dan `_augft` hanya untuk lampiran
  eksperimen augmentasi.
- Tangkapan layar 13 berkas di `docs/proposal/screenshots/`, termasuk dua versi mobile.
  Masih tampilan lama (biru gelap), wajib diambil ulang setelah aplikasi petugas memakai tema hijau.
- Data pendukung `docs/proposal/data/demo_sites.json` dan `demo_indices.json`.
- Lisensi pihak ketiga `docs/LICENSES.md`, termasuk catatan BirdNET CC BY-NC-SA 4.0.

## 3. Isi paket aplikasi yang diminta panitia

- Kode sumber: repo ini. Versi yang dipakai saat submit harus ditandai, misalnya
  `git tag -a submit-usb2026 -m "Paket submit USB 2026"`, supaya berkas lokal yang
  diserahkan bisa dicocokkan dengan commitnya.
- Dump database: `make backup` menghasilkan dump dan salinan audio di `ops/backups/`.
  Prosedur pemulihannya ada di `ops/RESTORE.md` dan sudah diuji lewat
  `ops/backup_selftest.sh`.
- Cara menjalankan lokal: `make up`, web di `http://localhost:3001`, API di
  `http://localhost:8000`. Akun contoh ada di `apps/api/app/seed.py`.

## 4. Sebelum mengirim URL software (6 sampai 9 Oktober)

- [x] gemahutan.site hidup dengan HTTPS, worker cascade jalan, pendaftaran tertutup,
      `ENVIRONMENT=production`.
- [ ] Aplikasi petugas dibuka dengan login per peran, tombol Masuk di halaman depan.
- [ ] Tiga akun juri dibuat admin (lihat `docs/AKSES_JURI.md`), sandi dikirim terpisah.
- [ ] SMTP Gmail diisi di server supaya reset sandi dan undangan terkirim.
- [ ] Tangkapan layar proposal diambil ulang dari tampilan baru.
- [ ] Waktu proses rekaman 60 menit diukur ulang di server produksi.
- [ ] Repo publik disinkron lewat `bash ops/sinkron_publik.sh` (atas izin pemilik).

## 5. Jadwal dari panduan

- 30 September 2026: pendaftaran peserta ditutup.
- 02 sampai 05 Oktober 2026: penyerahan persyaratan administrasi, yaitu proposal.
- 06 sampai 09 Oktober 2026: pengumpulan revisi proposal, poster, dan software
  beserta URL.
- 13 Oktober 2026: technical meeting.
- 22 Oktober 2026: seleksi lomba di Kampus F8, presentasi 10 menit lalu tanya jawab
  15 menit.
- 9 November 2026: penyerahan berkas aplikasi, PPT, dan manual book untuk finalis.
- 19 November 2026: final di Auditorium Kampus D4 lantai 6.

Catatan: KRS aktif dan pas foto 3x4 tidak disebut pada syarat kategori Software
Development, jadi konfirmasi dulu ke panitia sebelum melampirkan.
