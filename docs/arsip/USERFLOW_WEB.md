> **Arsip, tidak berlaku lagi.** Dipindahkan ke `docs/arsip/` pada 3 Oktober 2026. Acuan yang
> berlaku: `docs/VISI_DAN_RUANG_LINGKUP.md`. Isi di bawah boleh dibaca untuk sejarah, tetapi
> jangan dijadikan dasar tugas.

# Userflow Web GemaHutan (rebuild)

Disusun 23 September 2026 untuk membangun ulang `apps/web` dari nol.
Versi lama dihapus karena tidak memenuhi standar UX. Sumber kebenaran:
`DESIGN.md`, `docs/MANUAL.md`, API riil dari `apps/api`, hasil ukur
terakhir (21 Sept 2026).

## 1. Prinsip UX

Tiga aturan yang menuntun setiap halaman:

1. **Satu layar, satu keputusan.** Setiap halaman dibuat围绕 satu
   pertanyaan atau satu aksi. Ranger datang dengan "apa yang gagal
   malam ini", bukan dengan "jelajahi dasbor".
2. **Data riil, bukan dekorasi.** Angka yang tampil berasal dari
   API. Angka kosong tetap kosong atau berlabel jelas, bukan
   placeholder berisi nama orang fiktif.
3. **Aksesibilitas terukur, bukan asumsi.** Tap target >= 44 px,
   kontras WCAG, fokus keyboard terlihat, navigasi tanpa mouse.

Arah visual dari `DESIGN.md` dipakai apa adanya:
- Dark default `#09090B`, kartu `#101010`, teks `#F4F4F5`.
- Aksi biru `#0033FF` (isi tombol), biru teks `#8AB0FF`.
- Aksen mint `#99FFE4` hanya untuk satu momen per halaman.
- Tanpafoto orang, tanpa testimoni, tanpa logo mitra, tanpa glow,
  tanpa animasi loop. Motion = hover dan transisi saja.
- Tipografi tunggal Plus Jakarta Sans.

## 2. Persona dan tujuan

Tiga peran utama, masing-masing dengan satu tugas inti:

| Peran | Tujuan utama | Hal yang tidak penting bagi dia |
|---|---|---|
| Ranger | Unggah rekaman dari lapangan, lihat apakah prosesnya jalan | Indeks soundscape, kalibrasi model, pengelolaan akun |
| Researcher | Verifikasi deteksi, unduh data untuk analisis, bandingkan spesies | Manajemen lokasi/perangkat, unggahan massal |
| Admin | Kelola lokasi, perangkat, akun, deploy | Verifikasi harian, audio waveform |

Layar disusun mengikuti peran, bukan mengikuti struktur API.

## 3. Peta layar (10 layar)

### Publik (tanpa login)
1. `/` Landing. Penjelasan singkat produk, alur kerja, CTA masuk.
2. `/masuk` Form login. Satu kolom email, satu kolom password, satu
   tombol. Tautan ke daftar kalau registrasi masih dibuka.

### Otentikasi
3. `/daftar` Form pendaftaran. Hanya muncul bila
   `ALLOW_REGISTRATION=true` di server. Setelah server publik,
   halaman ini disembunyikan dan diganti pesan "Pendaftaran ditutup,
   minta admin".

### Dalam aplikasi (perlu login)
4. `/dashboard` Ringkasan yang menjawab: ada rekaman gagal yang
   harus diulang, ada batch yang belum selesai, ada verifikasi
   yang belum ditinjau.
5. `/rekaman` Daftar rekaman dengan filter. Tabel, bukan kartu
   (keputusan kolum dari keputusan ranger: mana yang harus diulang).
6. `/rekaman/{id}` Detail satu rekaman: pemutar audio, spektrogram
   dengan marker deteksi, daftar deteksi dengan aksi verifikasi,
   peta lokasi, status job, lokasi (`range_m` ditampilkan kalau ada).
7. `/rekaman/baru` Unggah. Pilih lokasi (wajib), perangkat (opsional),
   satu sampai dua puluh berkas, lihat progres per berkas.
8. `/rekam` Rekam langsung dari peramban. Paksa pilih lokasi dulu.
9. `/spesies` Daftar 25 spesies + spesies dari BirdNET. Klik masuk
   ke `/spesies/{id}` dengan riwayat deteksi dan grafik.
10. `/lokasi` Peta + daftar lokasi. Tambah/edit hanya untuk admin.
11. `/perangkat` Daftar perangkat perekam dengan kolom jarak antar
    mikrofon dan acuan jarak. Tambah/edit hanya untuk admin.
12. `/laporan` Ringkasan siap cetak. Angka dibaca dari
    `/api/v1/stats/*`. Tombol "Cetak" memunculkan dialog cetak
    peramban.
13. `/model` Status mesin, ambang, batas yang sudah diukur. Versi
    model, kapan dilatih, support per spesies.
14. `/admin/akun` Daftar akun, ubah peran, hapus akun. Hanya admin.
15. `/dokumentasi` Versi web dari `docs/MANUAL.md`.

Total 15 layar. Tidak ada layar "Settings" terpisah: pengaturan
akun (nama, ganti kata sandi) jadi tab di `/profil`.

## 4. Alur utama per peran

### Ranger

**Alur A: unggah rekaman lapangan**
1. Buka `/dashboard`. Lihat "3 rekaman gagal kemarin" + "1 batch
   selesai 80%".
2. Klik "Lihat yang gagal" -> `/rekaman?status=failed`.
3. Klik satu rekaman gagal -> `/rekaman/{id}`.
4. Lihat spektrogram, baca pesan galat, klik "Ulangi pemrosesan".
5. Kembali ke dashboard, klik "Unggah rekaman" -> `/rekaman/baru`.
6. Pilih lokasi "Taman Kota" (sudah disimpan), pilih perangkat
   "AudioMoth-01", pilih 4 berkas, klik "Unggah".
7. Lihat bilah progres per berkas (bukan progres global).
8. Selesai unggah, kembali ke dashboard otomatis.

**Alur B: rekam dari peramban**
1. Buka `/rekam`.
2. Pilih lokasi dulu (tombol mulai disabled sebelum lokasi dipilih).
3. Klik "Mulai rekam", mikrofon merekam webm/opus 128 kbps.
4. Klik "Berhenti", lihat ringkasan durasi, klik "Kirim".
5. Otomatis masuk ke `/rekaman/{id}`.

**Alur C: lihat hasil yang sudah diproses**
1. Buka `/rekaman`.
2. Filter lokasi, rentang tanggal, spesies, keyakinan minimum.
3. Klik salah satu -> `/rekaman/{id}`.
4. Putar audio dengan waveform. Klik marker di spektrogram, lompat
   ke detik itu. Klik deteksi di daftar, lihat waktu dan keyakinan.
5. Kalau species terlihat, klik nama spesies -> `/spesies/{id}`.

### Researcher

**Alur D: verifikasi deteksi**
1. Buka `/dashboard`. Lihat "12 deteksi menunggu verifikasi".
2. Klik angka -> `/rekaman?needs_review=1` (filter rekaman dengan
   deteksi yang belum diverifikasi).
3. Pilih satu -> `/rekaman/{id}`.
4. Klik deteksi pertama, pilih Benar/Salah/Ragu. Tombol keyboard:
   `B` benar, `S` salah, `R` ragu. Fokus pindah otomatis ke
   deteksi berikutnya.
5. Lihat indikator progress verifikasi di header rekaman.

**Alur E: unduh data untuk analisis**
1. Buka `/laporan`.
2. Pilih rentang tanggal, filter lokasi, filter status verifikasi.
3. Klik "Unduh CSV" -> file terunduh lewat
   `/api/v1/exports/verified?format=csv&status=correct&site=...`.

### Admin

**Alur F: tambah lokasi baru**
1. Buka `/lokasi`.
2. Klik "Tambah lokasi" (muncul hanya untuk admin).
3. Isi nama, habitat, elevasi, klik titik di peta untuk isi lat/lon
   (bukan ketik manual).
4. Klik "Simpan".

**Alur G: kalibrasi perangkat**
1. Buka `/perangkat`.
2. Pilih "AudioMoth-01" -> `/perangkat/{id}`.
3. Isi `mic_spacing_m`, `reference_distance_m`, `reference_level_db`.
4. Klik "Simpan". Status berubah dari "Belum dikalibrasi" ke
   "Terkalibrasi 10 m, -23 dBFS".

**Alur H: kelola akun**
1. Buka `/admin/akun`.
2. Lihat tabel: nama, email, peran, status, terakhir masuk.
3. Klik peran di baris, ganti ke `researcher`.
4. Klik hapus untuk akun uji, konfirmasi modal.

## 5. Komponen bersama

Komponen yang dipakai lintas halaman, semua sesuai aturan R-04 sampai
R-13 dari antislop:

- **AppShell**: sidebar kiri ringkas (logo, navigasi peran, keluar)
  + area konten. Tanpa top bar terpisah. Sidebar bisa diciutkan di
  mobile.
- **TopBarKonten**: judul halaman, sub judul 1 baris, tombol aksi
  utama di kanan.
- **Tabel**: baris bisa diklik ke detail. Filter di atas, bukan
  tersembunyi. Paginasi di bawah, "X sampai Y dari Z".
- **EmptyState**: judul "Belum ada rekaman", sub "Unggah berkas
  pertama di /rekaman/baru", tombol "Unggah rekaman".
- **ErrorState**: judul "Gagal memuat", sub "Coba lagi atau periksa
  jaringan", tombol "Coba lagi".
- **LoadingState**: skeleton baris tabel, bukan spinner penuh.
- **KartuStat**: satu kartu per metrik yang benar-benar penting,
  maksimal 3 per halaman. Angka + label + delta (kalau ada
  pembanding).
- **SpektrogramPlayer**: waveform + spektrogram + marker deteksi,
  klik marker lompat ke detik itu.
- **PetaLokasi**: MapLibre + OpenStreetMap, marker #4C7DFF, popup
  nama + habitat, attribution tetap.
- **FormField**: label di atas, helper di bawah, pesan error di
  bawah helper, semua связано dengan `aria-describedby`.
- **DialogKonfirmasi**: judul + isi + dua tombol (batal, konfirmasi).
  Tombol konfirmasi merah untuk aksi destruktif.

## 6. Status state yang harus ada di setiap halaman

Sesuai R-27 antislop. Setiap halaman wajib punya:

| State | Isi minimal |
|---|---|
| Loading | Skeleton baris tabel atau kartu |
| Kosong | Sebab + satu aksi untuk mengisi |
| Error | Pesan galat yang bisa dibaca + tombol coba lagi |
| Sukses | Konten utama |

State kosong bukan "No data". Contoh untuk `/rekaman`:
- Judul: "Belum ada rekaman"
- Sub: "Unggah berkas audio pertama untuk mulai"
- Tombol: "Unggah rekaman" -> `/rekaman/baru`

## 7. Aksesibilitas dan performa

Wajib:

- Kontras teks min 4.5:1 untuk teks biasa, 3:1 untuk teks besar.
  Palet di `DESIGN.md` sudah memenuhi, kecuali `--muted-foreground`
  di atas `--background` (sudah 5.9:1).
- Tap target >= 44 x 44 px pada viewport 390 px.
- Fokus keyboard terlihat: ring `#4C7DFF` setebal 2 px di luar
  elemen, bukan `outline: none` tanpa ganti.
- Setiap form punya label yang связано dengan input (`htmlFor` +
  `id`).
- Modal bisa ditutup dengan `Escape`, fokus kembali ke tombol
  pembuka.
- Sidebar di mobile: tombol hamburger, panel geser, `inert` saat
  tertutup.
- Setiap halaman harus lulus Lighthouse mobile >= 90 untuk
  Performance dan Accessibility.

## 8. Pertanyaan terbuka untuk dikonfirmasi

Lima keputusan yang belum dikunci, butuh jawaban sebelum bangun:

1. Sidebar collapsible atau bottom tab di mobile? Saya condong
   bottom tab (lebih mudah dijangkau jempol), tapi ranger di
   lapangan lebih suka sidebar collapsible karena pakai HP di
   holder.
2. Apakah `/laporan` perlu ekspor PDF dari server, atau cukup
   dialog cetak peramban? Saya condong cetak peramban dulu, PDF
   server menyusul kalau lomba butuh.
3. Apakah tema gelap saja, atau perlu toggle terang? `DESIGN.md`
   sudah memutuskan tanpa toggle. Pertahankan.
4. Tabel rekaman: virtual scroll atau paginasi? Data lapangan
   bisa ribuan. Saya condong virtual scroll dengan paginasi
   sebagai fallback.
5. Peta di `/rekaman/baru` perlu interaktif atau sekadar lihat
   koordinat? Saya condong interaktif (klik titik = isi lat/lon).

## 9. Urutan build

Minggu 1: AppShell, otentikasi, dasbor kosong.
Minggu 2: daftar rekaman + detail (inti ranger).
Minggu 3: unggah + rekam + status job (SSE).
Minggu 4: peta lokasi + perangkat + kalibrasi (admin).
Minggu 5: spesies + laporan + verifikasi (researcher).
Minggu 6: audit a11y, Lighthouse, deploy publik.
