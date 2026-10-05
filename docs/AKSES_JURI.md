# Panduan Akses Juri / Judge Access Guide

> Versi bilingual: Bahasa Indonesia diikuti English. Versi Inggris bukan
> terjemahan kata-per-kata, tapi menyampaikan isi yang sama.

Dokumen ini untuk juri USB 2026 kategori Software Development. Tidak memuat
kata sandi -- kredensial dikirim lewat jalur terpisah saat VPS sudah menyala.

This document is for USB 2026 Software Development judges. No passwords are
written here -- credentials are sent separately once the VPS is live.

---

## URL Aplikasi / Application URL

| | URL |
|---|---|
| Situs / Site | https://gemahutan.site |
| Dokumentasi / Docs | https://gemahutan.site/dokumentasi |
| Kode sumber / Source | https://github.com/azrahudaya/gemahutan |

> **Keadaan 3 Oktober 2026 / Status.** Saat ini hanya halaman depan dan dokumentasi yang terbuka.
> "Coba contoh" di halaman depan bisa dipakai tanpa akun. Aplikasi petugas sedang dibuka
> kembali dengan login per peran; bagian di bawah menjelaskan keadaan setelah itu.
> Only the landing page and docs are open today; "Coba contoh" works without an account.
> The staff app is being reopened behind role-based login, as described below.

GemaHutan dibuat untuk petugas konservasi: admin kawasan, peneliti, dan ranger. Server
produksi tidak berisi data demo, jadi juri mengisi datanya sendiri dengan berkas contoh.
GemaHutan is built for conservation staff. The production server holds no demo data, so
judges create their own data from the sample files.

---

## Akun Juri / Judge Accounts

Admin membuat tiga akun juri, satu per peran. Kata sandi dikirim ke panitia lewat jalur
terpisah, tidak ditulis di repo.
The admin creates three judge accounts, one per role. Passwords are sent separately.

| Email | Peran / Role | Yang bisa dicoba / What to try |
|---|---|---|
| `juri@gemahutan.id` | admin | Semua, termasuk akun, lokasi, perangkat, spesies prioritas / Everything incl. accounts, sites, devices, priority species |
| `juri-peneliti@gemahutan.id` | researcher | Semua rekaman, verifikasi, ekspor, dashboard, peta, laporan / All recordings, verification, export, dashboard, map, report |
| `juri-ranger@gemahutan.id` | ranger | Rekam, unggah, hasil rekamannya sendiri, simulasi lokasi / Record, upload, own results, location simulation |

---

## Mencoba Aplikasi / Trying the Application

1. **Unggah sebagai ranger / Upload as ranger.** Masuk sebagai `juri-ranger`, buka `/upload`,
   pilih lokasi, unggah satu atau beberapa berkas dari `ml/demo_audio/` (tabel di bawah).
   Tunggu progres 100%, lalu buka rekamannya.
2. **Rekam dari peramban / Record in browser.** Buka `/rekam` di HP, izinkan mikrofon, rekam,
   hentikan. Butuh MediaRecorder (Chrome, Edge, Firefox).
3. **Verifikasi sebagai peneliti / Verify as researcher.** Masuk sebagai `juri-peneliti`. Rekaman
   ranger tadi terlihat. Buka satu, pilih Benar, Salah, atau Ragu pada deteksinya.
4. **Lihat kawasan / Area view.** Sebagai peneliti atau admin: `/dashboard`, `/sites` (peta),
   `/laporan`, lalu ekspor CSV/JSON data terverifikasi.
5. **Bandingkan peran / Compare roles.** Sebagai ranger, rekaman milik akun lain tidak
   terlihat, dan menu dashboard, ekspor, Model, Perangkat tidak ada.

| Berkas / File | Spesies / Species | Durasi |
|---|---|---|
| `xc-938488.mp3` | Pycnonotus goiavier (Merbah Cerukcuk) | 0:24 |
| `xc-46911.mp3` | Merops philippinus (Kirik-kirik Laut) | 0:15 |
| `xc-151987.mp3` | Centropus bengalensis (Bubut Alang-alang) | 0:19 |
| `xc-105148.mp3` | Amaurornis phoenicurus (Kareo Padi) | 0:19 |
| `xc-38341.mp3` | Lonchura punctulata (Bondol Peking) | 0:19 |
| `xc-1157493.mp3` | Anthreptes malacensis (Burung Madu Kelapa) | 0:15 |
| `xc-350538.mp3` | Corvus macrorhynchos (Gagak Kampung) | 0:21 |
| `xc-598171.mp3` | Geopelia striata (Perkutut Jawa) | 0:33 |

Atribusi dan lisensi tiap klip: `ml/demo_audio/ATTRIBUTION.csv`.

---

## Batasan yang Jujur / Honest Limitations

Yang ini HARUS dibaca sebelum menilai. Semua angka adalah hasil pengukuran,
bukan perkiraan:

These MUST be read before judging. All numbers are measured, not estimated:

### Cakupan model / Model coverage

- Model lokal hanya mengenal **25 spesies** dari sekitar 1.800 spesies burung
  Indonesia (1,4%). Lihat daftar lengkap di halaman `/species` atau
  `docs/MANUAL.md` bagian 7.
- Deteksi spesies di luar 25 itu bergantung pada BirdNET zero-shot, yang
  ambangnya lebih konservatif.

- The local classifier covers only **25 species** out of ~1,800 Indonesian
  bird species (1.4%). Full list at `/species` or `docs/MANUAL.md` section 7.
- Detection outside those 25 relies on BirdNET zero-shot with more
  conservative thresholds.

### Akurasi / Accuracy

| Kondisi / Condition | Akurasi / Accuracy | Catatan / Note |
|---|---|---|
| Audio bersih Xeno-canto (uji) | **0,677** (F1 0,654) | Klip berkualitas A-B, bukan rekaman lapangan / Quality A-B clips, not field recordings |
| Rekaman ponsel iNaturalist | **0,508** | Turun signifikan dari audio bersih / Significant drop from clean audio |
| Audio lapangan Xeno-canto kualitas C-E | **0,659** | Lebih representatif untuk kondisi lapangan / More representative of field conditions |
| Deteksi palsu pada pengecoh | **0,617** berkas memicu | 62% klip non-target masih memicu deteksi / 62% of non-target clips still trigger detection |

### Rekaman panjang / Long recordings

- 60 menit audio diproses dalam **99 detik** di CPU (3,4x realtime). Belum diukur ulang di server produksi.
- RAM: **3,9 GB** saat memproses 60 menit. Server target 4 vCPU / 8 GB.
- Pemrosesan per blok 3 detik -- memori tidak tumbuh dengan durasi.

- 60 minutes of audio processed in **99 seconds** on CPU (3.4x realtime), not yet re-measured on the production server.
- RAM usage: **3.9 GB** for 60 minutes. Target server: 4 vCPU / 8 GB.
- Block-based processing (3-second chunks) -- memory does not grow with
  duration.

### Yang belum ada / What's missing

- **Belum ada rekaman lapangan asli.** Semua pengukuran memakai klip arsip
  (Xeno-canto, iNaturalist) dan simulasi ffmpeg (hujan, angin, kota, jarak).
  Akurasi di hutan tropis sebenarnya belum terukur.
- **Verifikator ahli belum dilibatkan.** Verifikasi deteksi di aplikasi masih
  contoh, belum divalidasi oleh ornitolog.
- **Simulasi degradasi bukan rekaman lapangan.** Skenario hujan, angin, kota,
  dan jarak dibuat dengan ffmpeg, bukan rekaman asli di kondisi tersebut.

- **No real field recordings yet.** All measurements use archival clips and
  ffmpeg simulations. Accuracy in actual tropical forest conditions is
  unmeasured.
- **No expert verifier involved yet.** Detection verifications in the app are
  demo examples, not validated by an ornithologist.
- **Degradation scenarios are simulated**, not field recordings.

---

## Arsitektur dan deploy / Architecture and deploy

Lihat `docs/ARCHITECTURE.md` dan `docs/DEPLOY.md`. Tanpa GPU; semua inferensi di CPU.
See `docs/ARCHITECTURE.md` and `docs/DEPLOY.md`. No GPU; all inference runs on CPU.

---

## Kontak

Tim GemaHutan -- Artya Epriliani (10124205) & Azra Hudaya (50423244)
Universitas Gunadarma 2026