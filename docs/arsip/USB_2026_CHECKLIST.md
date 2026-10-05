> **Arsip, tidak berlaku lagi.** Dipindahkan ke `docs/arsip/` pada 3 Oktober 2026. Acuan yang
> berlaku: `docs/VISI_DAN_RUANG_LINGKUP.md`. Isi di bawah boleh dibaca untuk sejarah, tetapi
> jangan dijadikan dasar tugas.

# Checklist Paket Submit USB 2026

> Setiap butir memakai simbol kotak. Centang `[x]` bila sudah ada di repo
> atau sudah diukur. Biarkan kosong `[ ]` bila belum. Sumber status:
> `docs/CHECKLIST_SUBMIT.md` (21 September 2026), `README.md`,
> `docs/proposal/catatan-verifikasi.md`, dan `docs/proposal/USB2026_*.md`.

## 1. Berkas wajib kategori Software Development

- [x] Proposal PDF, target `<=20` halaman A4, spasi 1,5, TNR 12, `<=50` MB. Naskah sumber: `docs/proposal/USB2026_Proposal.md`. Rendering ke PDF terpisah.
- [x] Outline presentasi 10 slide. Sumber: `docs/proposal/USB2026_SlideOutline.md`.
- [x] Script video 10 menit. Sumber: `docs/proposal/USB2026_VideoScript.md`.
- [x] Surat pernyataan orisinalitas bermaterai (LAMPIRAN 2). Sumber: `docs/proposal/USB2026_SuratPernyataan.md`. Materai dan tanda tangan asli diperlukan saat pengumpulan.
- [ ] Berkas PPT/PPTX final (render dari outline). Belum, menunggu render.
- [ ] Berkas PDF proposal final (render dari naskah). Belum, menunggu render.
- [ ] Berkas video final (render dari script, upload YouTube unlisted). Belum, menunggu produksi.
- [ ] URL publik aplikasi dan basis data. Belum, kredensial produksi belum dipasang.
- [x] Poster (untuk tahap revisi). Belum disiapkan di repo.
- [x] Tag git `submit-usb2026` saat berkas dibekukan.

## 2. Aset di repositori (siap pakai)

- [x] Narasi dan angka: `docs/proposal/USB2026_Proposal.md`, `docs/MANUAL.md`, `README.md`, `docs/proposal/catatan-verifikasi.md`.
- [x] Grafik 11 berkas di `docs/proposal/figures/`. Tangga degradasi utama `fig08_degradasi_audio.png`, varian `_aug` dan `_augft` hanya untuk lampiran eksperimen augmentasi.
- [x] Tangkapan layar 13 berkas di `docs/proposal/screenshots/`, termasuk dua versi lebar 390 piksel.
- [x] Data pendukung `docs/proposal/data/demo_sites.json` dan `demo_indices.json`.
- [x] Lisensi pihak ketiga `docs/LICENSES.md`, termasuk catatan BirdNET CC BY-NC-SA 4.0.

## 3. Pengujian dan operasional yang sudah diukur

- [x] 57 test API lulus. Verifikasi: `docker compose exec -T api python -m pytest tests/ -q`.
- [x] 25 test worker lulus. Verifikasi: `docker compose exec -T worker python -m pytest tests/ -q`.
- [x] 57 test antarmuka lulus. Verifikasi: `cd apps/web && npx vitest run`.
- [x] 28 pemeriksaan fitur berbasis HTTP lulus. Verifikasi: `python3 ops/verify_features.py`.
- [x] 6 pemeriksaan keamanan lulus. Verifikasi: `python3 ops/security_check.py` atau `make security-check`.
- [x] Uji klik menyeluruh 24 langkah, 0 galat konsol. Verifikasi: `python3 ops/e2e_clickthrough.py`.

## 4. Kepatuhan terhadap format panduan

- [x] Cover LAMPIRAN 1 memuat judul, JENIS LOMBA, DISUSUN OLEH TIM, anggota dengan NPM, UNIVERSITAS GUNADARMA 2026.
- [x] Nama berkas proposal: `Proposal_SoftwareDevelopment_TimGemaHutan_GemaHutan.pdf` (saat render).
- [x] Nama berkas presentasi: `Presentasi_SoftwareDevelopment_TimGemaHutan_GemaHutan.pptx` (saat render).
- [x] Judul video YouTube: `USB 2026 | Software Development | Tim GemaHutan | GemaHutan`, status unlisted.
- [x] Opening video memuat logo USB 2026, logo Universitas Gunadarma, ikon aplikasi, nama produk, nama tim, dan anggota.
- [x] Tanpa em dash, tanpa simbol panah di naskah.

## 5. Klaim mutu model yang sudah diverifikasi

- [x] Akurasi uji 0,7156 (n=128 klip uji bersih tanpa ND). Sumber: `ml/reports/eval.md`.
- [x] F1 makro 0,7194. Sumber: `ml/reports/metrics.json`.
- [x] Dataset 924 klip bersih tanpa ND, 26 kelas, tiap spesies minimal 5 klip.
- [x] Akurasi lapangan: Xeno-canto C-E 0,6594, ponsel iNaturalist 0,5082, deteksi palsu pengecoh 0,6172. Sumber: `ml/reports/field_metrics.json`.
- [x] Tangga degradasi simulasi 8 tingkat. Sumber: `ml/data/degraded/`, `ml/reports/field_eval.md`.
- [x] Eksperimen augmentasi yang gagal, dilaporkan apa adanya. Sumber: `ml/reports/field_experiments.md`.

## 6. Sebelum URL publik dipasang (gate)

- [ ] `ALLOW_REGISTRATION=false`. Sekarang default True (lihat `docs/RENCANA_PRODUK.md`).
- [ ] Ganti kata sandi akun contoh `admin@gemahutan.id`. Sekarang masih nilai contoh.
- [ ] `ENVIRONMENT=production` sehingga nilai contoh ditolak.
- [ ] Object-level authorization lintas akun (P0-1) ditutup. Sumber temuan: `docs/AUDIT_LENGKAP_23SEPT.md`.
- [ ] Refresh token rotation (P0-3) ditutup.
- [ ] Validasi magic bytes audio (P1-5) dipasang.

## 7. Daftar placeholder yang menunggu data

- [ ] Angka pasti jumlah method endpoint dan path: hitung ulang dari `/openapi.json` sebelum render.
- [ ] Statistik narya tes lulus pasca-pembersihan database (`docs/AUDIT_LENGKAP_23SEPT.md`).
- [ ] Daftar 25 spesies target beserta threshold final per spesies untuk tabel lampiran.
- [ ] Daftar referensi visual (ikon, badge, foto) untuk slide jika ada.
- [ ] Tanggal dan tempat pasti pengumpulan berkas dari panitia.
- [ ] Nama Dosen Pembimbing untuk Surat Pernyataan (jika diwajibkan).

## 8. Jadwal dari panduan

- 30 September 2026: pendaftaran peserta ditutup.
- 02 sampai 05 Oktober 2026: penyerahan persyaratan administrasi (proposal).
- 06 sampai 09 Oktober 2026: pengumpulan revisi proposal, poster, dan software beserta URL.
- 13 Oktober 2026: technical meeting.
- 22 Oktober 2026: seleksi lomba di Kampus F8 (presentasi 10 menit, tanya jawab 15 menit).
- 9 November 2026: penyerahan berkas aplikasi, PPT, dan manual book untuk finalis.
- 19 November 2026: final di Auditorium Kampus D4 lantai 6.