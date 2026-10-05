# Script Video Presentasi USB 2026 (10 Menit)

> **Panduan produksi.** Video berdurasi 10 menit, resolusi minimal 1920x1080
> landscape, format YouTube unlisted, judul
> `USB 2026 | Software Development | Tim GemaHutan | GemaHutan`. Tautan tetap
> aktif sampai rangkaian USB selesai. Opening wajib memuat logo USB 2026, logo
> Universitas Gunadarma, ikon aplikasi, nama produk, nama tim, dan seluruh
> anggota.

## Daftar Waktu

| Mulai | Durasi | Bagian |
|---|---|---|
| 0:00 | 5 detik | Opening logo |
| 0:05 | 25 detik | Nama produk, tim, anggota |
| 0:30 | 60 detik | Masalah |
| 1:30 | 5 menit | Demo alur aplikasi |
| 6:30 | 60 detik | Model info |
| 7:30 | 30 detik | Lisensi dan ucapan |
| 8:00 | 90 detik | Montase spektrogram dan tim |
| 9:30 | 30 detik | Call to action |

---

## 0:00 (5 detik) Opening Logo

**Visual:**
- Hitam ke hijau hutan perlahan (0,5 detik).
- Logo USB 2026 di pojok kiri atas.
- Logo Universitas Gunadarma di pojok kanan atas.
- Ikon aplikasi GemaHutan (gema suara dalam lingkaran hijau) di tengah.
- Transisi fade ke slide nama produk.

**Audio:** nada ambient hutan 2 detik, lalu jingle pendek USB 2026 1 detik.

**Teks di layar:** "Universitas Gunadarma, USB 2026, Software Development".

**Narasi:** (tidak ada, murni visual).

---

## 0:05 (25 detik) Nama Produk, Tim, Anggota

**Visual:**
- Judul besar: "GemaHutan".
- Subjudul: "Pemantauan Satwa Hutan berbasis Bioakustik dengan Cascade Classifier 26 Spesies Indonesia".
- Baris: "TIM GEMAHUTAN, Universitas Gunadarma 2026".
- Foto kedua anggota (Artya Epriliani dan Azra Hudaya) di pojok bawah.

**Audio:** musik latar instrumental lembut, beat 60 BPM.

**Narasi (suaranya Artya):**
> "Selamat datang. Kami tim GemaHutan dari Universitas Gunadarma. Produk kami bernama GemaHutan, aplikasi untuk pemantauan satwa hutan dengan bioakustik. Tim kami terdiri dari Artya Epriliani sebagai ketua dan Azra Hudaya sebagai anggota. Produk ini kami ajukan untuk kategori Software Development pada USB 2026."

---

## 0:30 (60 detik) Masalah

**Visual:**
- Frame 1 (15 detik): peta Indonesia dengan tutupan hutan yang menyusut, animasi sederhana.
- Frame 2 (15 detik): foto pengamat lapangan dengan binokular, caption "Survei manual: 3 sampai 5 hari kunjungan per titik".
- Frame 3 (15 detik): kamera jebak dengan siluet burung yang tidak tertangkap kamera, caption "Camera trap gagal untuk spesies vokal".
- Frame 4 (15 detik): grafik model global, satu garis ambang untuk semua spesies, caption "BirdNET satu ambang, spesies lokal tidak konsisten".

**Audio:** suara hutan asli (jernih, 5 detik), lalu musik tegang ringan.

**Narasi (suara Azra):**
> "Indonesia punya lebih dari 1.800 spesies burung, dan sebagian besar hidup di hutan yang terus menyusut. Memantau satwa secara rutin itu mahal: butuh pengamat ahli, perjalanan jauh, dan waktu berjam-jam untuk satu titik. Kamera jebak melengkapi data visual, tapi gagal untuk spesies yang lebih sering terdengar daripada terlihat. Model bioakustik global seperti BirdNET sudah ada. Masalahnya, model itu pakai satu ambang untuk semua spesies, sehingga hasilnya tidak konsisten untuk spesies lokal Indonesia. Itulah celah yang kami tutup dengan GemaHutan."

---

## 1:30 (5 menit = 300 detik) Demo Alur Aplikasi

**Tata letak:** layar penuh ke aplikasi GemaHutan di `http://localhost:3001`, dengan narasi pelan. Setiap langkah dijeda 5 detik untuk memberi waktu kamera merekam.

### 1:30 sampai 1:50 (20 detik) Masuk

**Visual:** layar masuk, ketik `admin@gemahutan.id`, masuk.

**Narasi (Artya):**
> "Pertama, masuk dengan akun contoh. Tiga peran tersedia: ranger untuk unggah, peneliti untuk verifikasi, admin untuk kelola."

### 1:50 sampai 2:10 (20 detik) Pilih Lokasi

**Visual:** peta lokasi, klik salah satu titik, tampilkan popup dengan koordinat.

**Narasi (Azra):**
> "Sebelum unggah, kita pilih lokasi. Koordinat ini dipakai model untuk menyaring spesies yang relevan di wilayah tersebut."

### 2:10 sampai 2:50 (40 detik) Unggah

**Visual:** halaman upload, drag and drop 3 berkas demo, status per berkas muncul.

**Narasi (Artya):**
> "Unggah satu atau sampai 20 berkas sekaligus. Format yang diterima: wav, mp3, flac, ogg, m4a, aac, opus, dan webm. Status tiap berkas terlihat jelas: berhasil, sedang proses, atau gagal dengan pesan galat."

### 2:50 sampai 4:00 (70 detik) Tunggu Job, Spektrogram Muncul

**Visual:** layar daftar rekaman, klik satu rekaman, panel deteksi muncul bertahap. Tahapan terlihat: antre, unduh, dekode, birdnet, klasifikasi, lokalisasi, indeks, spektrogram, selesai.

**Narasi (Azra):**
> "Worker mengambil job dari antrean Redis. Sembilan tahap dijalankan: dekode, BirdNET, klasifikasi cascade, lokalisasi, indeks akustik, spektrogram. Kemajuan ditampilkan via SSE tanpa muat ulang. Spektrogram di-cache: render pertama 0,27 detik, berikutnya 0,05 detik."

### 4:00 sampai 5:00 (60 detik) Verifikasi Deteksi

**Visual:** klik satu deteksi, muncul tombol Benar, Salah, Ragu. Klik Benar, status berubah.

**Narasi (Artya):**
> "Peneliti dapat menandai setiap deteksi sebagai benar, salah, atau ragu. Hasil verifikasi disimpan dengan jejak waktu dan pemeriksa, lalu dapat diunduh lewat endpoint exports. Verifikasi positif menjadi bahan latih untuk versi model berikutnya."

### 5:00 sampai 6:30 (90 detik) Lihat Arah dan Jangkauan

**Visual:** buka halaman lokasi, peta dengan kerucut arah datang dan lingkaran jarak. Klik satu deteksi, panel menampilkan azimuth, arah mata angin, sudut kembar.

**Narasi (Azra):**
> "Untuk rekaman multi-kanal, sistem menghitung arah datang suara dengan GCC-PHAT. Arah ditampilkan sebagai kerucut pada peta. Kalau perangkat belum dikalibrasi, jarak dibiarkan kosong dan aplikasi menampilkan alasannya, bukan angka kosong. Susunan mikrofon segaris tidak memisahkan arah depan dari belakang, dan itu kami tampilkan sebagai arah kembar supaya pengguna tidak salah baca."

---

## 6:30 (60 detik) Model Info

**Visual:** split screen. Kiri: grafik `figures/fig02_f1_per_spesies.png`. Kanan: grafik `figures/fig08_degradasi_audio.png`.

**Narasi (Artya):**
> "Model kami dilatih pada 8.356 klip bersih tanpa lisensi NoDerivatives, 26 kelas dengan minimal 5 klip per spesies. Akurasi uji 0,7795, F1 makro 0,7194, support per spesies 3 sampai 8 klip. Tangga degradasi delapan tingkat menunjukkan arah perubahan mutu: kontrol reencode 0,68, hujan ringan 0,61, gabungan berat 0,28. Pada audio lapangan nyata: korpus Xeno-canto berkualitas rendah 0,66, rekaman ponsel iNaturalist 0,51, deteksi palsu pada pengecoh 0,62. Catatan penting: degradasi ini simulasi ffmpeg, bukan rekaman lapangan, dan rekaman lapangan sendiri belum kami kumpulkan, jadi angka ini batas atas mutu."

---

## 7:30 (30 detik) Lisensi dan Ucapan Terima Kasih

**Visual:** background hijau gelap. Logo BirdNET, Xeno-canto, iNaturalist, scikit-maad, librosa, FastAPI, Next.js, PostgreSQL, PostGIS, MapLibre, MinIO. Di bawah: "MIT untuk kode, lisensi pihak ketiga di docs/LICENSES.md. BirdNET-Analyzer CC BY-NC-SA 4.0 (non-komersial)."

**Narasi (Azra):**
> "GemaHutan open source dengan lisensi MIT. BirdNET kami pakai dengan lisensi CC BY-NC-SA 4.0, atribusi penuh. Terima kasih kepada Xeno-canto, iNaturalist, scikit-maad, dan komunitas open source yang memungkinkan karya ini."

---

## 8:00 (90 detik) Montase Spektrogram Indah dan Tim

**Visual:** montase 90 detik. Urutan:
- 8:00 sampai 8:30: 6 spektrogram berbeda dari `ml/demo_audio/` (jenis, pagi, siang, malam), transisi fade.
- 8:30 sampai 8:50: foto tim saat gladi resik, foto saat pegang mikrofon di lapangan.
- 8:50 sampai 9:00: tangkapan layar peta dengan beberapa kerucut arah datang.

**Audio:** suara hutan dengan kicauan burung asli, fading lembut ke musik instrumental.

**Narasi (Artya):** (hanya 1 kalimat)
> "Setiap spektrogram di sini adalah rekaman nyata. Inilah hutan yang ingin kami dengar."

---

## 9:30 (30 detik) Call to Action

**Visual:** background hijau hutan. Logo GemaHutan besar di tengah. Di bawah: "GemaHutan, biosonar untuk hutan Indonesia." Kontak demo: `http://localhost:3001`. Footer: "USB 2026, Software Development, Universitas Gunadarma, 2026".

**Audio:** nada jingle akhir, 3 detik.

**Narasi (Azra):**
> "GemaHutan, biosonar untuk hutan Indonesia. Demo aplikasi tersedia di localhost:3001 pada mesin lokal kami. Terima kasih untuk waktu dan perhatian tim juri. Kami siap menjawab pertanyaan di sesi tanya jawab."

(Artya menimpali, 5 detik terakhir):
> "Terima kasih."

---

## Produksi

- Resolusi: 1920x1080 landscape.
- Format: MP4 atau MOV, H.264.
- Frame rate: 30 fps.
- Audio: mono atau stereo 48 kHz, level dialog konsisten.
- Subtitle: opsional, font putih dengan outline hitam, ukuran 36 pt setara.
- Render final: judul YouTube persis sesuai panduan.
- Status: unlisted.
- Daftar putar: tidak perlu.
- Deskripsi: cantumkan tautan repo dan `docs/proposal/USB2026_Proposal.md`.