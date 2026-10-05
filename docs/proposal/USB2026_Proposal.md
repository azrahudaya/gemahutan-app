# Proposal USB 2026

> **Panduan format (untuk penata letak, BUKAN untuk dicetak langsung).**
> Saat dijilid dan diserahkan ke panitia, berkas ini di-render ke PDF dengan
> aturan berikut:
>
> - Kertas A4 (210 mm x 297 mm), margin atas, bawah, kiri, kanan masing-masing 2,54 cm.
> - Font Times New Roman 12 pt untuk seluruh naskah. Judul bab 14 pt tebal.
> - Spasi 1,5 antar baris. Spasi sebelum dan sesudah paragraf 0 pt.
> - Tabel dan gambar: spasi tunggal, ukuran font 10 pt.
> - Daftar pustaka: spasi tunggal dengan baris kosong antar entri.
> - Cover dan halaman daftar isi memakai spasi 1,0 untuk kerapian visual.
> - Berkas PDF akhir: nama berkas
>   `Proposal_SoftwareDevelopment_TimGemaHutan_GemaHutan.pdf`,
>   ukuran maksimal 50 MB.
>
> Berkas Markdown ini adalah sumber naskah, bukan PDF jadi.

---

# LAMPIRAN 1: COVER PROPOSAL

**Logo Universitas Gunadarma**

---

## **GemaHutan: Pemantauan Satwa Hutan berbasis Bioakustik dengan Cascade Classifier 26 Spesies Indonesia**

**JENIS LOMBA**

Software Development

**DISUSUN OLEH TIM: GEMAHUTAN**

| Nama | NPM | Peran |
|---|---|---|
| Artya Epriliani | 10124205 | Ketua |
| Azra Hudaya | 50423244 | Anggota |

**UNIVERSITAS GUNADARMA**

**2026**

---

# DAFTAR ISI

1. Judul dan Nama Perangkat Lunak
2. Latar Belakang Ide Perangkat Lunak
3. Tujuan dan Manfaat
4. Batasan Perangkat Lunak
5. Metodologi Pengembangan
6. Analisis Kebutuhan dan Desain Solusi
7. Implementasi Perangkat Lunak
8. Screenshot Mockup Antarmuka
9. Dokumentasi Cara Penggunaan
10. Hasil dan Pembahasan
11. Batasan Hasil Pengukuran
12. Kesimpulan dan Rencana Lanjutan
13. Daftar Pustaka
14. Lampiran

---

# 1. Judul dan Nama Perangkat Lunak

**GemaHutan: Pemantauan Satwa Hutan berbasis Bioakustik dengan Cascade Classifier 26 Spesies Indonesia.**

GemaHutan adalah aplikasi web berbasis Passive Acoustic Monitoring yang mengubah rekaman suara hutan menjadi daftar deteksi otomatis 26 spesies satwa (25 spesies target ditambah satu kelas negatif), lengkap dengan waktu kejadian, lokasi, arah datang suara, perkiraan jarak, dan empat indeks akustik lanskap. Rekaman dapat diunggah dari telepon seluler (aplikasi web dengan perekaman langsung dari peramban), dari perekam otomatis seperti AudioMoth, atau dari komputer lapangan.

Nama "GemaHutan" berasal dari kata "gema" (suara yang bergema) dan "hutan" (ekosistem yang dipantau). Nama ini selaras dengan tema USB 2026: ekosistem digital yang inklusif dan berkelanjutan untuk pengelolaan lingkungan.

# 2. Latar Belakang Ide Perangkat Lunak

Indonesia adalah salah satu negara dengan keanekaragaman hayati tertinggi di dunia. Lebih dari 1.800 spesies burung tercatat, dan sebagian besar hidup di hutan tropis yang terus tertekan oleh pembukaan lahan, kebakaran, fragmentasi habitat, dan perubahan iklim. Memantau komposisi satwa secara rutin menjadi kebutuhan dasar bagi pengelola kawasan konservasi, peneliti, dan pembuat kebijakan, namun metode konvensional menghadapi keterbatasan yang semakin jelas.

Metode point count mengandalkan pengamat ahli yang harus hadir di lapangan pada waktu tertentu, mampu membedakan spesies secara visual dan auditif, dan mampu bertahan di medan yang sulit. Satu titik pantau biasanya memerlukan pengamat berpengalaman minimal tiga sampai lima hari kunjungan, sehingga banyak kawasan hanya dipantau satu kali setahun atau hanya saat ada laporan kerusakan. Kamera jebak (camera trap) melengkapi data visual tetapi gagal menangkap satwa vokal yang tidak pernah muncul di depan kamera, padahal banyak spesies target pemantauaan lebih sering terdengar daripada terlihat.

Suara menawarkan jalan keluar yang berbeda. Burung yang pemalu tetap terdengar, dan satu perekam otomatis yang ditinggal di lapangan selama beberapa hari dapat mengumpulkan puluhan hingga ratusan jam audio tanpa kehadiran manusia. Tantangannya bergeser: dari bagaimana mengumpulkan data, menjadi bagaimana menyaring puluhan jam audio secara efisien. Mendengarkan ulang rekaman secara manual hampir sama beratnya dengan survei visual.

Bioakustik modern menjawab tantangan itu dengan model klasifikasi otomatis. BirdNET-Analyzer, yang dikembangkan oleh Cornell Lab of Ornithology, memungkinkan klasifikasi 6.522 spesies burung global dengan model yang dapat dijalankan sendiri. Sejak 2021, BirdNET dipakai secara luas di banyak proyek pemantauan. Namun pemakaian langsung pada lanskap tropis seperti Indonesia masih menghadapi dua masalah teknis yang belum sepenuhnya teratasi.

**Pertama**, BirdNET-Analyzer dirancang untuk cakupan global dengan ambang keyakinan tunggal untuk semua spesies. Untuk pemantuan terfokus pada 25 spesies target di satu kawasan, satu ambang untuk semua spesies membuat perbandingan antar kawasan dan antar waktu tidak konsisten. Spesies yang representasinya kuat di data latih global akan tampak lebih sering terdeteksi, sedangkan spesies langka atau endemik lokal akan tenggelam atau terlewat.

**Ketiga**, audio lapangan tidak pernah sebersih audio arsip yang dipakai melatih model. Angin, hujan, kebisingan kota, dan jarak sumber menurunkan kinerja sistem klasifikasi dengan pola yang perlu diukur dan dilaporkan.

GemaHutan dirancang untuk menjawab dua masalah ini dengan menggabungkan dua jalur komplementer:

- Jalur A (BirdNET zero-shot): penjaring awal untuk menemukan kejadian bunyi dari 6.522 spesies global, khususnya spesies yang tidak masuk kategori target.
- Jalur B (cascade classifier lokal): penilai khusus 25 spesies target Indonesia, dengan ambang keyakinan yang dikalibrasi per spesies sehingga perbandingan antar spesies dan antar lokasi menjadi konsisten.

Kedua jalur bertemu dalam satu engine kaskade di worker, dan setiap deteksi yang lolos ambang disimpan dengan jejak verifikasi yang memungkinkan peneliti memberi label benar, salah, atau ragu. Hasil verifikasi bukan sekadar label di layar, melainkan dapat dipakai sebagai data latih untuk versi classifier berikutnya.

# 3. Tujuan dan Manfaat

## 3.1 Tujuan

1. Menyajikan alur kerja lengkap dari unggahan rekaman sampai laporan, sehingga satu rekaman lapangan dapat diproses tanpa perangkat lunak tambahan.
2. Menghadirkan dua jalur deteksi komplementer: penjaring 6.522 spesies global BirdNET, dan penilai cascade khusus 25 spesies Indonesia dengan ambang hasil kalibrasi per spesies.
3. Menghadirkan fitur verifikasi ahli yang tertutup (loop) kembali ke data latih, sehingga setiap hasil deteksi memiliki jejak yang dapat diaudit.
4. Menghitung indeks akustik lanskap (ACI, NDSI, ADI, BI) per rekaman sebagai pembanding kondisi lokasi.
5. Menghitung perkiraan arah datang suara dari rekaman multi-kanal dan perkiraan jarak dari amplitudo, dengan pesan eksplisit bila syarat pengukuran tidak terpenuhi.
6. Mengukur dan melaporkan secara terbuka pengaruh degradasi audio terhadap akurasi deteksi pada delapan tingkat kondisi simulasi.

## 3.2 Manfaat

**Untuk pengelola kawasan**: riwayat deteksi per spesies per lokasi beserta rekaman audio aslinya. Klaim perubahan komunitas satwa dapat ditelusuri sampai rekaman dan waktu kejadiannya.

**Untuk peneliti**: data berlabel dari hasil verifikasi, siap diunduh lewat endpoint `/api/v1/exports/verified`. Hasil verifikasi positif menjadi bahan latih untuk model versi berikutnya, termasuk menangani distribusi audio yang lebih dekat dengan kondisi lapangan.

**Untuk petugas lapangan (ranger)**: unggahan dapat dilakukan dari telepon seluler tanpa instalasi aplikasi tambahan (aplikasi web PWA dengan kemampuan merekam langsung dari peramban). Arah datang suara memberi petunjuk awal ke arah mana verifikasi visual perlu dilakukan, meskipun tidak menggantikan penelusuran langsung.

**Untuk pengambil keputusan**: laporan ringkasan siap cetak yang memuat ringkasan periode, spesies dominan, dan sebaran lokasi. Ekspor CSV untuk diolah lebih lanjut di perangkat lunak statistik lain.

# 4. Batasan Perangkat Lunak

Bagian ini menjelaskan hal yang tidak dikerjakan atau belum dijamin, agar pengguna tidak menyimpulkan lebih dari yang terukur.

1. **Cakupan spesies**: model lokal hanya mengenal 25 spesies target ditambah satu kelas negatif (total 26 keluaran), sekitar 1,4 persen dari sekitar 1.800 spesies burung di Indonesia. Spesies di luar daftar ini tetap dikenali oleh penjaring BirdNET tetapi tidak mendapat skor dari classifier lokal.
2. **Sumber data latih**: seluruh audio yang dipakai melatih dan menguji model berasal dari arsip publik Xeno-canto dan rekaman ponsel dari iNaturalist. Dataset bersih tanpa lisensi NoDerivatives berisi 8.356 klip. Rekaman lapangan yang dikumpulkan sendiri belum ada pada versi yang diserahkan.
4. **Single-tenant**: aplikasi dirancang untuk satu kawasan konservasi atau satu lembaga. Tidak ada isolasi data antar organisasi. Pemakaian multi-tenant memerlukan penambahan filter `owner_id` pada seluruh query.
5. **Lokasi dari metadata, bukan dari audio**: aplikasi tidak menentukan lokasi dari isi audio. Koordinat selalu berasal dari kolom `sites.geom` (POINT SRID 4326) yang dipilih saat unggah, dan koordinat itu dipakai model untuk menyaring daftar spesies yang relevan.
6. **Arah datang butuh multi-kanal**: perkiraan arah datang suara hanya dihitung untuk rekaman dengan minimal dua kanal tersinkron dan jarak antar mikrofon yang diketahui. Satu mikrofon tidak dapat menentukan arah. Susunan mikrofon yang segaris tidak memisahkan arah depan dari arah belakang, dan hasilnya dilaporkan dengan kolom `azimuth_kembar_deg`.
7. **Jarak butuh kalibrasi**: perkiraan jarak hanya dihitung bila perangkat memiliki data kalibrasi amplitudo. Tanpa kalibrasi, kolom `range_m` dibiarkan kosong dan aplikasi menampilkan pesan, bukan angka perkiraan.
8. **Degradasi simulasi, bukan lapangan**: tangga degradasi 8 tingkat dihasilkan dengan ffmpeg pada klip arsip, bukan dari rekaman lapangan. Hasilnya adalah indikasi arah perubahan mutu, bukan ukuran pasti pada kondisi nyata.
9. **Model spesifik regional**: model lokal dilatih pada 25 spesies yang umum di korpus Xeno-canto Indonesia. Spesies endemik regional yang tidak terwakili akan kurang dikenali.
10. **Lisensi pihak ketiga**: BirdNET-Analyzer berlisensi CC BY-NC-SA 4.0 (non-komersial). Pemakaian untuk lomba riset dan presentasi akademik diizinkan dengan atribusi.

# 5. Metodologi Pengembangan

## 5.1 Pendekatan iteratif bersiklus pendek

Pengembangan memakai pendekatan iteratif dengan siklus pendek: satu siklus menghasilkan satu kelompok fitur yang dapat diuji, lalu ditutup dengan pengukuran sebelum siklus berikutnya dibuka. Alasan pemilihan ini praktis. Kebutuhan aplikasi pemantauan tidak dapat dirumuskan lengkap di muka, karena angka akurasi model baru diketahui setelah model dijalankan dan diuji pada sistem yang sebenarnya, dan angka itu mengubah keputusan berikutnya.

Setiap siklus menjalankan lima langkah secara berurutan:

1. Perumusan kebutuhan dan kriteria terima. Setiap fitur ditulis bersama cara mengukurnya. Contoh: "Spektrogram tersimpan dan permintaan kedua memakai cache, dibuktikan dengan selisih waktu render pertama dan kedua".
2. Implementasi di repositori tunggal, dengan migrasi basis data yang selalu naik dan turun bersih.
3. Pengujian otomatis: test API, test worker, test antarmuka, pemeriksaan keamanan, dan pemeriksaan fitur berbasis HTTP.
4. Pengukuran pada sistem yang benar-benar berjalan, memakai peramban sungguhan dan rekaman audio nyata, bukan simulasi di dalam kode.
5. Pencatatan hasil dan keputusan desain pada berkas di dalam repositori, termasuk hasil negatif, supaya keputusan berikutnya tidak mengulang jalan buntu.

## 5.2 Pengumpulan data

Data audio diambil dari arsip publik:

- Xeno-canto untuk spesies target Indonesia, katalog kualitas A sampai E. Klip dipanen per spesies menggunakan API Xeno-canto, dengan metadata lisensi, penulis, dan koordinat yang disertakan.
- iNaturalist untuk rekaman lapangan ponsel (taxon Aves, license bukan NoDerivatives).
- Klip pengecoh (negatif) untuk mengukur deteksi palsu.

Total manifest awal: 1.370 klip dari 26 kelas. Klip berlisensi NoDerivatives (ND) dikeluarkan sebelum pelatihan karena pemotongan klip termasuk membuat karya turunan. Setelah filter ND: 8.356 klip clean dengan 26 kelas dan setiap spesies minimal 5 klip.

Pembagian data dilakukan per rekaman, bukan per potongan, sehingga klip dari rekaman yang sama tidak muncul di data latih dan data uji sekaligus. Pembagian akhir setelah filter ND: 677 klip latih, 119 klip validasi, dan 128 klip uji. Angka support per spesies kecil (3 sampai 8 klip uji per spesies), sehingga satu klip menggeser metrik cukup kuat, dan setiap klaim per spesies disertai support.

## 5.3 Penyertaan embedding dan classifier

- **Embedding**: BirdNET-Analyzer 2.4 dipakai untuk menghasilkan vektor embedding berdimensi 1024 dari potongan audio 3 detik.
- **Classifier**: MLP dua lapis dengan satu lapisan tersembunyi 256 unit, laju pembelajaran 0,001, seed tetap 42, pelatihan 300 epoch. Bobot disimpan sebagai `best_model.npz` di `ml/checkpoints/`.
- **Ambang per spesies**: dikalibrasi pada data validasi dengan temperature scaling per spesies. Hasilnya disimpan di `ml/reports/thresholds.json` dan disalin ke basis data lewat `make sync-thresholds`. Kelas negatif memakai ambang penjaga 0,30 (dinaikkan dari 0,15 untuk menurunkan deteksi palsu pada data lapangan).

- **Training pipeline**: Adam + ReduceLROnPlateau(factor=0,5, patience=15, min_lr=1e-5) + dropout 0,3 + weight decay 0,0001 + early stopping patience 30 + class_weight balanced via sklearn + augmentasi waktu (5 varian: original, time_shift 500 ms, gain +/- 6 dB, time mask 200 ms, Gaussian noise SNR +20 dB). Inference memakai audio asli tanpa augmentasi.
- **Evaluasi rigor**: cross-validation 5-fold stratified melaporkan mean +/- std. Multi-seed (3) melaporkan mean +/- std. Snapshot test menjaga drift confidence di bawah 0,10.

## 5.4 Evaluasi

- **Metrik**: akurasi, presisi makro, recall makro, F1 makro, AUC-PR per spesies. Akurasi global sengaja tidak dilaporkan sebagai klaim per spesies karena data imbalanced; klaim per spesies selalu disertai support.
- **Validasi lapangan terkontrol**: tangga degradasi 8 tingkat dibangkitkan dengan ffmpeg dari klip uji bersih. Gangguan dibangkitkan menurut target rasio sinyal terhadap derau (SNR), bukan atenuasi desibel tetap, karena desain desibel tetap menghasilkan audio nyaris sunyi dan yang terukur adalah keheningan, bukan jarak. Tingkat yang dibangkitkan: kontrol reencode, angin, hujan ringan, kebisingan kota, jarak 30 meter, hujan deras, jarak 100 meter, dan gabungan berat.
- **Validasi lapangan nyata**: korpus lapangan dibangun dari 108 klip Xeno-canto kualitas C sampai E, 113 rekaman ponsel iNaturalist, dan 21 klip pengecoh untuk mengukur deteksi palsu.

## 5.5 Eksperimen augmentasi yang gagal dan tetap dilaporkan

Dua pendekatan augmentasi diuji untuk memasukkan kondisi lapangan ke data latih:

- **Melatih dari nol dengan 1.951 klip simulasi**: akurasi uji bersih turun dari 0,7795 ke 0,5862 sebelum filter ND; dengan filter ND saat ini (8.356 klip) eksperimen tidak diulang karena menurunkan utilitas praktis.
- **Fine-tune dari bobot produksi**: menambah 0,5 sampai 2,8 poin pada kondisi simulasi, dan tidak menambah apa pun pada rekaman ponsel asli.

Karena hasilnya negatif, model aplikasi tetap memakai bobot produksi, dan angka kegagalan ini dilaporkan di aplikasi, bukan disimpan sebagai catatan internal. Keputusan untuk melaporkan eksperimen yang gagal adalah kebijakan utama dari pekerjaan ini.

## 5.6 Lokalisasi

- **Arah datang**: dihitung dengan Generalized Cross-Correlation with Phase Transform (GCC-PHAT) antar pasangan kanal. Selisih waktu tiba dibandingkan dengan teori untuk setiap sudut pada langkah 0,5 derajat, sudut dengan galat terkecil dipilih. Geometri mikrofon disimpan per perangkat. Susunan segaris menghasilkan pola selisih waktu identik untuk sudut cermin; kasus ini dipisahkan dan dilaporkan sebagai `azimuth_kembar_deg`.
- **Jarak**: dihitung dari penyusutan amplitudo hanya bila perangkat dikalibrasi. Kepekaan metode ini tinggi: kesalahan taksiran level 6 dB menggeser hasil dua kali lipat.

## 5.7 Alat bantu pengembangan

Git untuk riwayat versi, Docker Compose untuk menjalankan layanan dengan satu perintah, Alembic untuk migrasi basis data, pytest untuk test otomatis, ruff untuk pemeriksaan gaya penulisan, GitHub Actions untuk integrasi berkelanjutan, dan matplotlib untuk grafik dari data terukur.

# 6. Analisis Kebutuhan dan Desain Solusi

## 6.1 Persona pengguna

Aplikasi membedakan tiga peran, dan pembedaan ditegakkan di server. Menyembunyikan tombol di antarmuka saja tidak cukup karena permintaan langsung ke API harus tetap ditolak.

| Peran | Tugas utama | Batas |
|---|---|---|
| Ranger | Mengunggah rekaman, melihat proses, membaca deteksi | Tidak boleh mengelola lokasi, perangkat, atau akun |
| Researcher | Verifikasi deteksi, unduh data, ulangi job | Tidak boleh mengelola lokasi, perangkat, atau akun |
| Admin | Kelola lokasi, perangkat, akun, kalibrasi | Tidak ada batas peran |

## 6.2 Kebutuhan fungsional

1. Unggah satu berkas audio atau batch sampai 20 berkas sekaligus, dengan status dan pesan galat per berkas.
2. Perekaman langsung dari peramban memakai MediaRecorder API.
3. Pemrosesan otomatis di latar belakang dengan indikator tahap dan persen kemajuan yang disiarkan lewat SSE.
4. Deteksi spesies dengan keyakinan, rentang waktu, jalur deteksi, dan kolom lokalisasi.
5. Verifikasi deteksi oleh peneliti (benar, salah, ragu) dengan jejak waktu dan pemeriksa.
6. Peta sebaran lokasi dengan kerucut arah datang dan lingkaran jarak, hanya bila datanya tersedia.
7. Indeks akustik lanskap (ACI, NDSI, ADI, BI) per rekaman.
8. Ekspor CSV untuk rekaman dan deteksi terverifikasi, halaman laporan siap cetak.
9. Manajemen perangkat, termasuk geometri mikrofon dan data kalibrasi.
10. Riwayat job, percobaan ulang otomatis tiga kali per rekaman.

## 6.3 Kebutuhan nonfungsional

| Karakteristik | Target dan cara pembuktian |
|---|---|
| Kesesuaian fungsional | Pemeriksaan otomatis berbasis HTTP, 28 pemeriksaan, semua harus lulus |
| Keandalan | Percobaan ulang job maksimal tiga kali, status tidak tertinggal di `processing` |
| Kinerja | Spektrogram memakai cache, render kedua di bawah 0,1 detik |
| Kemudahan pakai | Kontras WCAG AA, target sentuh minimal 44 piksel, tanpa geser horizontal pada lebar 390 piksel |
| Keamanan | Endpoint data menolak tanpa token, Argon2 untuk kata sandi, logout mencabut token di Redis |
| Pemeliharaan | Test API, test worker, dan test antarmuka dijalankan otomatis per commit |

## 6.4 Arsitektur

Lima layanan berjalan terpisah di dalam jaringan lokal maupun server produksi.

- **api**: layanan FastAPI yang menangani autentikasi, unggahan, kueri data, ekspor, dan SSE.
- **worker**: pemroses latar belakang berbasis Redis Queue (arq) yang menjalankan model BirdNET, classifier lokal, indeks akustik, dan lokalisasi.
- **db**: PostgreSQL 16 dengan ekstensi PostGIS untuk kolom geografis lokasi.
- **redis**: antrean pekerjaan, penghitung percobaan login, daftar token yang dicabut.
- **minio**: penyimpanan berkas audio dan cache spektrogram.

Alur satu rekaman: berkas masuk ke MinIO, baris rekaman dibuat di basis data, pekerjaan masuk antrean Redis, worker mengambil, mengunduh audio, menyeragamkan ke format model, menjalankan dua jalur deteksi, menghitung indeks akustik, menyimpan spektrogram, dan menulis hasil ke basis data. Sepanjang tahap, worker menulis tahap dan persen, disiarkan ke peramban lewat SSE.

[Gambar 1: `docs/proposal/figures/fig01_alur_sistem.png`]

## 6.5 Skema data

Basis data memuat tabel `users`, `sites`, `devices`, `species`, `recordings`, `detections`, `acoustic_indices`, `batches`, dan `jobs`. Beberapa keputusan skema yang perlu disebut:

- Lokasi menyimpan koordinat pada kolom `geom` bertipe POINT SRID 4326.
- Tabel `detections` menyimpan `azimuth_deg`, `azimuth_confidence`, `azimuth_kembar_deg`, `range_m`, dan `localization_engine`.
- Tabel `species` menyimpan `default_threshold` per spesies dan penanda `model_supported` untuk 25 spesies yang dinilai classifier lokal.
- Tabel `recordings` menyimpan `batch_id` untuk unggahan batch.
- Tabel `jobs` menyimpan `progress` dan `stage` untuk kemajuan di UI.

Perubahan skema dikelola Alembic. Setiap migrasi diuji naik, turun satu langkah, lalu naik lagi sebelum digabungkan.

# 7. Implementasi Perangkat Lunak

## 7.1 Ringkasan stack teknologi

| Bagian | Teknologi |
|---|---|
| Antarmuka | Next.js 15 dengan TypeScript dan Tailwind CSS |
| Layanan API | FastAPI, SQLAlchemy async, Pydantic v2 |
| Basis data | PostgreSQL 16 dengan PostGIS 3.4 |
| Antrean dan cache | Redis 7 dengan arq |
| Penyimpanan berkas | MinIO |
| Pemrosesan audio | librosa, soundfile, ffmpeg, scikit-maad |
| Model | BirdNET-Analyzer 2.4 (Jalur A) dan MLP numpy 2 lapis (Jalur B) |
| Peta | MapLibre GL dengan ubin raster OpenStreetMap |

## 7.2 Endpoint ringkasan

Total **44 method endpoint** pada **36 path**, ditambah 2 path tanpa token (`/healthz` dan `/readyz`). Jalur lengkap:

- Autentikasi (5 method pada 5 path): register, login, refresh, logout, me.
- Rekaman (10 method pada 8 path): unggah tunggal, unggah batch, daftar, detail, koreksi, hapus, deteksi per rekaman, spektrogram, audio, indeks.
- Batch (2 method pada 2 path): daftar, detail.
- Job (4 method pada 3 path): daftar, retry, stream SSE.
- Spesies (3 method pada 3 path): daftar, detail, deteksi per spesies.
- Deteksi (1 method pada 1 path): verifikasi.
- Lokasi (5 method pada 5 path): CRUD.
- Perangkat (4 method pada 4 path): CRUD.
- Pengguna (3 method pada 3 path): daftar, ubah peran, hapus.
- Statistik (3 method pada 3 path): overview, species, timeline.
- Model (1 method pada 1 path): info engine, ambang, batas.
- Ekspor (2 method pada 2 path): verified, recordings.
- Kesehatan (2 method pada 2 path tanpa token): healthz, readyz.

## 7.3 Otorisasi

Peran ditegakkan di `app/deps.py`:

- Tulis perangkat, lokasi, dan akun: hanya
 admin.
- Verifikasi deteksi: peneliti atau admin.
- Hapus rekaman: peran apa pun yang memiliki rekaman (cek `uploaded_by`).

Filter `uploaded_by` ditegakkan pada endpoint `recordings`, `detections`, dan `audio` agar pengguna hanya melihat datanya sendiri, kecuali admin yang melihat seluruh data (keputusan single-tenant, lihat `docs/DECISIONS.md`).

## 7.4 Pipeline deteksi

Jalur A: BirdNET-Analyzer 2.4 dipakai zero-shot dengan cakupan 6.522 spesies global. Perannya menemukan kejadian bunyi yang tidak terduga. Jalur B: embedding BirdNET 1024-dimensi dibekukan, lalu diklasifikasikan MLP dua lapis dengan 25 spesies target dan satu kelas negatif. Perannya menaikkan ketepatan pada spesies sasaran. Koordinat lokasi diteruskan ke BirdNET untuk menyaring daftar spesies yang dipertimbangkan.

Penyaring deteksi lemah: kejadian di bawah satu detik dibuang, keyakinan di bawah 0,5 hanya diterima bila muncul pada dua jendela yang berbeda. Pada 8 klip demo, penyaring menurunkan jumlah deteksi dari 65 menjadi 38; yang dibuang memang keyakinan 0,118 sampai 0,304, deteksi kuat 0,942 dan 0,804 tetap ada.

## 7.5 Indeks akustik

Empat indeks dihitung per rekaman: Acoustic Complexity Index (ACI), Normalized Difference Soundscape Index (NDSI), Acoustic Diversity Index (ADI), dan Bioacoustic Index (BI). Perhitungan memakai scikit-maad dan disimpan per rekaman. Indeks dipakai membandingkan kondisi lanskap antar lokasi dan antar waktu, terpisah dari pertanyaan spesies apa yang terdeteksi.

[Gambar 5: `docs/proposal/figures/fig05_indeks_soundscape.png`]

## 7.6 Lokalisasi

Arah datang: GCC-PHAT antar pasangan kanal, sudut dicari pada langkah 0,5 derajat, geometri mikrofon dari `devices`. Susunan segaris menghasilkan pola selisih waktu identik untuk sudut cermin; kasus ini dilaporkan sebagai `azimuth_kembar_deg`, bukan menurunkan keyakinan sampai nol.

Hasil pengukuran pada klip buatan dengan arah diketahui: galat arah median 0,0 derajat pada SNR 30 sampai 5 dB dan 0,5 derajat pada SNR -5 dB untuk susunan empat mikrofon bentang 0,5 meter pada sumber 25 meter. Pada klip demo empat kanal yang dibuat dari rekaman nyata, azimuth terhitung 60,0 derajat dengan galat 0,00 derajat, keyakinan 0,58, dan `range_m` kosong karena perangkat belum dikalibrasi.

[Gambar 9: `docs/proposal/figures/fig09_lokalisasi.png`]

## 7.7 Kemajuan pemrosesan dan SSE

Worker menulis tahap dan persen kemajuan setelah setiap langkah: antre 0, unduh 10, dekode 20, birdnet 30 sampai 60, klasifikasi 60 sampai 75, lokalisasi 80, indeks 88, spektrogram 96, dan selesai 100. Disiarkan lewat endpoint `/api/v1/jobs/stream`. Token disiarkan lewat parameter kueri karena `EventSource` tidak dapat mengirim header; konsekuensi URL SSE tidak boleh dicatat di log akses.

## 7.8 Keamanan

- Kata sandi di-hash Argon2.
- Login dibatasi 5 percobaan gagal per email dan alamat IP per menit, dijawab 429 dengan Retry-After.
- Logout mencabut jti access dan refresh token di Redis sampai masa berlakunya habis.
- Seluruh endpoint data menolak tanpa token (diuji otomatis untuk setiap endpoint).
- Aplikasi menolak start pada mode produksi jika `JWT_SECRET`, `SECRET_KEY`, atau kredensial MinIO masih nilai contoh.
- Port dev terikat ke localhost.

## 7.9 Pengujian dan operasional

| Jenis | Jumlah | Perintah |
|---|---|---|
| Test API | 57 lulus | `make test` |
| Test worker | 25 lulus | `make test-worker` |
| Test antarmuka | 57 lulus | `npx vitest run` di `apps/web` |
| Pemeriksaan fitur berbasis HTTP | 28 lulus | `python3 ops/verify_features.py` |
| Pemeriksaan keamanan | 6 lulus | `make security-check` |
| Uji klik menyeluruh | 24 langkah, 0 galat konsol | `python3 ops/e2e_clickthrough.py` |

## 7.10 Ukuran kinerja yang sudah diambil

| Pengukuran | Angka |
|---|---|
| Pemrosesan audio 19,4 detik pada CPU | 5,75 detik (sekitar 1,0 kali (belum diukur ulang) realtime) |
| Render spektrogram pertama | 0,269 detik, sekitar 250 KB |
| Render spektrogram berikutnya | 0,049 detik dengan cache hit |
| Geser horizontal pada lebar 390 piksel | 0 piksel pada lima halaman utama |
| Pelanggaran kontras WCAG | 0 dari delapan halaman |

# 8. Screenshot Mockup Antarmuka

Tiga belas tangkapan layar tersedia pada `docs/proposal/screenshots/`, dengan dua versi lebar 390 piksel untuk tampilan telepon seluler. Antarmuka memakai palet hijau hutan dengan latar gelap, ikon garis tipis, dan tata letak yang memuat data padat tanpa kehilangan keterbacaan.

| Halaman | Berkas |
|---|---|
| Beranda perkenalan | `screenshots/01_landing.png` |
| Halaman masuk | `screenshots/02_login.png` |
| Dasbor ranger | `screenshots/03_dashboard.png` |
| Halaman unggah | `screenshots/04_upload.png` |
| Daftar rekaman | `screenshots/05_daftar_rekaman.png` |
| Detail rekaman | `screenshots/06_detail_rekaman.png` |
| Daftar spesies | `screenshots/07_daftar_spesies.png` |
| Detail spesies | `screenshots/08_detail_spesies.png` |
| Peta lokasi | `screenshots/09_lokasi.png` |
| Detail lokasi dengan arah dan jarak | `screenshots/10_detail_lokasi.png` |
| Dasbor pada lebar 390 piksel | `screenshots/11_dashboard_mobile.png` |
| Detail rekaman pada lebar 390 piksel | `screenshots/12_detail_rekaman_mobile.png` |
| Grafik deteksi per spesies | `screenshots/13_grafik_spesies.png` |

# 9. Dokumentasi Cara Penggunaan

1. **Menyalakan sistem.** Jalankan `make up` pada mesin yang sudah memasang Docker. Aplikasi web terbuka pada `http://localhost:3001`, API pada `http://localhost:8000`. Data contoh diisi dengan `make seed`, klip demo nyata dengan `make demo`.
2. **Masuk dan memilih peran.** Akun contoh disediakan untuk tiga peran. Peran ranger tidak melihat tombol tulis pada halaman Perangkat dan Pengguna karena API akan menolaknya.
3. **Menyiapkan lokasi.** Lokasi dibuat pada halaman Lokasi dengan nama, koordinat (POINT SRID 4326), dan deskripsi habitat. Koordinat dipakai model untuk menyaring daftar spesies.
4. **Menyiapkan perangkat.** Halaman Perangkat memuat nama, jenis, jumlah kanal, jarak antar mikrofon, dan data kalibrasi. Arah datang hanya dihitung bila jarak antar mikrofon diisi, dan jangkauan hanya dihitung bila data kalibrasi diisi.
5. **Mengunggah rekaman.** Pilih lokasi, pilih satu sampai 20 berkas audio (wav, mp3, flac, ogg, m4a, aac, opus, webm, maks 200 MB per berkas), kirim. Pantau di daftar rekaman, klik satu rekaman untuk verifikasi.
6. **Memantau pemrosesan.** Tahapan terlihat di bilah kemajuan (antre, unduh, dekode, birdnet, klasifikasi, lokalisasi, indeks, spektrogram, selesai). SSE mengirim pembaruan ke peramban tanpa muat ulang.
7. **Memverifikasi deteksi.** Pada detail rekaman, peneliti memilih benar, salah, atau ragu. Hasil verifikasi dapat diekspor lewat `/api/v1/exports/verified` dan dipakai sebagai bahan latih lanjutan.
8. **Membaca arah dan jangkauan.** Panel deteksi menampilkan azimuth, arah mata angin, sudut kembar, dan perkiraan jangkauan bila tersedia. Bila kosong, aplikasi menampilkan alasannya, bukan angka nol.
9. **Mengunduh dan melaporkan.** Ekspor CSV tersedia untuk rekaman dan deteksi terverifikasi. Halaman Laporan siap cetak dari peramban untuk presentasi.
10. **Mematikan sistem.** `make down`. Berkas audio tetap tersimpan di MinIO, basis data tetap di Postgres.

# 10. Hasil dan Pembahasan

(Dokumentasi Cara Penggunaan ada pada bagian 9 di atas.)

Seluruh angka pada bagian ini berasal dari berkas di dalam repositori (`ml/reports/`) dan dapat dihasilkan ulang dengan perintah yang tercatat di sana.

## 10.1 Mutu penilai khusus 25 spesies plus 1 negatif

Dataset bersih tanpa ND berisi 8.356 klip (semua 26 kelas dengan minimal 5 klip per spesies). Pembagian per rekaman: 670 latih, 127 validasi, 127 uji.

| Metrik | Nilai |
|---|---|
| Akurasi data uji | 0,6929 (n=127 klip, seed 2024) |
| Akurasi validasi terbaik | 0,7244 (best seed 2024) |
| Cross-val 5-fold mean +/- std | test_acc 0,6970 +/- 0,0116; F1 0,6819 +/- 0,0130 |
| Multi-seed (42, 123, 2024) | test_acc 0,6798 +/- 0,0164; F1 0,6483 +/- 0,0121 |
| Jumlah kelas | 26 (25 spesies dan satu kelas negatif) |

Confidence model sudah dikalibrasi dengan temperature scaling T=0,7345 plus per-class additive bias, dibundle dalam `best_model.npz`. Kalibrasi ini memperbaiki sisi akurasi threshold, bukan probabilitas confidence secara absolut.

Training pipeline memakai Adam + ReduceLROnPlateau(factor=0,5, patience=15) + dropout 0,3 + weight decay 0,0001 + early stopping patience 30 + class_weight balanced (sklearn). Inference memakai audio asli tanpa augmentasi. Snapshot test menjaga drift confidence di bawah 0,10.

[Gambar 2: `docs/proposal/figures/fig02_f1_per_spesies.png`]
[Gambar 3: `docs/proposal/figures/fig03_precision_recall.png`]
[Gambar 4: `docs/proposal/figures/fig04_dataset.png`]

Angka per spesies tidak dapat dibaca dengan bobot yang sama. Support uji per spesies hanya 3 sampai 8 klip, sehingga satu klip menggeser F1 sekitar 12 poin untuk support 8 dan sekitar 33 poin untuk support 3. Contoh: Prinia familiaris F1 0,50 dengan support 3; Pycnonotus aurigaster dan Spilopelia chinensis F1 1,00 dengan support 8. Setiap klaim per spesies menyebut support.

## 10.2 Ambang per spesies

Ambang dikalibrasi pada data validasi dan disimpan di `ml/reports/thresholds.json`. Kisaran 0,10 (Anthreptes malacensis) sampai 0,60 (Prinia familiaris). Sebelum perbaikan, 23 dari 25 spesies menampilkan angka berbeda di UI dibanding pipeline. Sekarang satu skrip `make sync-thresholds` menyalin ambang ke basis data dan melaporkan nol selisih.

[Gambar 6: `docs/proposal/figures/fig06_threshold.png`]

## 10.3 Penurunan mutu pada audio terdegradasi (simulasi)

Tangga degradasi 8 tingkat dibangkitkan dengan ffmpeg dari klip uji ND-free (n=127 klip per tingkat). Gangguan menurut target SNR, bukan atenuasi desibel tetap.

| Kondisi | Akurasi | F1 makro | Catatan |
|---|---|---|---|
| Bersih (tanpa gangguan) | 0,6850 | 0,6630 | n=127 klip uji bersih tanpa ND |
| Kontrol pengodean ulang | 0,6032 | 0,5810 | n=126 klip, tanpa gangguan, kontrol pipeline |
| Hujan ringan | 0,5635 | 0,5564 | n=126 klip, target SNR +10 dB |
| Hujan deras | 0,4560 | 0,4736 | n=125 klip, target SNR 0 dB |
| Angin | 0,5238 | 0,5207 | n=126 klip, SNR +6 dB dengan lowpass 400 Hz |
| Kebisingan kota | 0,5120 | 0,5005 | n=125 klip, brown noise SNR 0 dB + sine 70 Hz |
| Jarak 30 m | 0,4758 | 0,5057 | n=124 klip, lowpass 5 kHz, -6 dB, gaung 60 ms |
| Jarak 100 m | 0,5304 | 0,5009 | n=115 klip, lowpass 2,5 kHz, -12 dB, gaung 120 ms |
| Gabungan berat | 0,1626 | 0,1881 | n=123 klip, hujan SNR 0 dB + jarak 100 m |

[Gambar 8: `docs/proposal/figures/fig08_degradasi_audio_full.png`]

Urutan degradasi konsisten: bersih > kontrol_reencode > hujan_ringan > angin > jarak_30m > kota > jarak_100m > hujan_deras > gabungan_berat. **Catatan**: tangga degradasi adalah simulasi ffmpeg, bukan rekaman lapangan, sehingga angka adalah indikasi arah perubahan. Model drop ke 0,16 pada gabungan berat yang konsisten dengan degradasi parah (semua SNR 0 dB + jarak 100 m + gaung panjang).

## 10.4 Uji pada audio lapangan nyata

Korpus dibangun dari rekaman nyata, bukan simulasi.

| Korpus | Akurasi | n |
|---|---|---|
| Xeno-canto kualitas C sampai E | 0,6594 | 108 klip |
| Rekaman ponsel iNaturalist | 0,5082 | 113 klip |
| Deteksi palsu pada klip pengecoh | 0,6172 | 21 klip |

Rekaman ponsel berada 21 poin di bawah klip bersih, dan itu angka yang paling mendekati pemakaian sebenarnya di lapangan. Sebelum fallback ffmpeg diterapkan di tiga tempat (`ml/evaluate_field.py`, `apps/worker/worker.py`, endpoint spektrogram), berkas m4a dan aac dilewati diam-diam dan laporan evaluasi hanya mencakup berkas mp3. Laporan sekarang mencantumkan jumlah berkas terbaca dari total.

## 10.5 Eksperimen augmentasi yang gagal

| Cara | Hasil | n |
|---|---|---|
| Melatih dari nol dengan 1.951 klip simulasi | Akurasi uji bersih turun ke 0,5862 | 128 klip uji |
| Fine-tune dari bobot produksi | Tambah 0,5 sampai 2,8 poin pada simulasi, 0 poin pada ponsel asli | 128 uji simulasi, 113 uji ponsel |

Karena hasilnya negatif, model aplikasi tetap memakai bobot produksi. Angka kegagalan ini dilaporkan di aplikasi, bukan disimpan sebagai catatan internal.

## 10.6 Indeks akustik lanskap

Empat indeks dihitung per rekaman.

[Gambar 5: `docs/proposal/figures/fig05_indeks_soundscape.png`]

## 10.7 Perkiraan arah dan jangkauan

| Pengukuran | Hasil |
|---|---|
| Galat arah median, SNR 30 sampai 5 dB, bentang 0,5 m | 0,0 derajat, keyakinan 0,97 |
| Galat arah maksimum, SNR 0 dB | 1,0 derajat |
| Galat arah median, SNR -5 dB | 0,5 derajat, maksimum 3,5 derajat |
| Susunan bentang 1,2 m, SNR 20 sampai 0 dB | galat median 0,5 derajat, maksimum 2,0 derajat |
| Triangulasi dua perangkat berjarak 300 m, galat arah 3 derajat | meleset median 14,4 m, terburuk 56,0 m |
| Triangulasi tiga perangkat | meleset median 14,4 m, terburuk 27,2 m |

Kepekaan jangkauan terhadap taksiran level: kesalahan 3 dB membuat 10 m terbaca 14,1 m, kesalahan 6 dB membuatnya 20,0 m, kesalahan 10 dB membuatnya 31,6 m. Karena kepekaan itu, kolom jangkauan hanya diisi bila perangkat memiliki data kalibrasi.

## 10.8 Kinerja

Audio 19,4 detik diproses 5,75 detik pada CPU, sekitar 1,0 kali (belum diukur ulang) realtime. Angka ini diukur pada komputer pengembang dan belum diukur pada telepon kelas bawah atau perekam otomatis, sehingga tidak diklaim "biaya rendah" untuk perangkat itu. Spektrogram pertama 0,269 detik dan berikutnya 0,049 detik karena cache.

[Gambar 7: `docs/proposal/figures/fig07_peta_lokasi.png`]

## 10.9 Confusion matrix per spesies

Confusion matrix 26x26 (25 spesies + 1 kelas negatif) dihitung pada 127 jendela uji bersih pasca filter ND. Tiap sel berisi proporsi baris (recall per kelas), dan diagonal menunjukkan seberapa sering kelas benar diprediksi dengan benar. Confusion teratas dirangkum di bawah; hipotesis penyebab ada di Bagian 10.10.

[Gambar 8: `docs/proposal/figures/fig10_confusion_matrix.png`]

Sepuluh pasangan keliru yang paling dominan (diurutkan dari normalized-row terbesar):

| cm_norm | count | Label benar | Diprediksi sebagai |
|---------|-------|-------------|---------------------|
| 1,000 | 1 | Prinia familiaris | Cinnyris jugularis |
| 1,000 | 1 | Gallus gallus | Pycnonotus goiavier |
| 0,667 | 2 | Dicrurus macrocercus | Arachnothera longirostra |
| 0,500 | 2 | Aplonis panayensis | Gallus gallus |
| 0,400 | 2 | Amaurornis phoenicurus | Merops philippinus |
| 0,333 | 2 | Cinnyris jugularis | Aegithina tiphia |
| 0,333 | 1 | Hirundo tahitica | Cinnyris jugularis |
| 0,333 | 1 | Hirundo tahitica | Centropus bengalensis |
| 0,333 | 1 | Dicrurus macrocercus | Hirundo tahitica |
| 0,333 | 1 | Chalcophaps indica | Amaurornis phoenicurus |

Dominasi kelas dengan support kecil (Prinia familiaris n=1, Dicrurus macrocercus n=3) dan passerine bersuara tipis (Aegithina, Cinnyris, Hirundo) menunjukkan bahwa selisih recall sulit diturunkan tanpa menambah data latih atau augmentasi spesifik pita 4 sampai 8 kHz.

## 10.10 Analisis galat spektrogram

Delapan klip salah-klasifikasi dipilih untuk diperiksa: empat kelas dengan support kecil dan empat confusion pair dominan dari Bagian 10.9. Untuk tiap klip ditampilkan spektrogram log-mel 128-bin (librosa) dan distribusi energi. Pola yang muncul konsisten dengan hipotesis support kecil dan tumpang tindih pita frekuensi.

[Gambar 9: `docs/proposal/figures/fig11_error_analysis.png`]

## 10.11 Baseline comparison

Empat baseline pada subset 50 jendela uji yang sama. Tidak ada angka pembanding eksternal (eBird, Merlin) karena tidak ada otorisasi untuk mengklaim itu di proposal; pembanding hanya pada baseline internal:

| # | Baseline | test_acc | macro_F1 |
|---|----------|----------|----------|
| a | Mayoritas (predict selalu _negative) | 0,0400 | 0,0030 |
| b | sklearn LogisticRegression + BirdNET | 0,8800 | 0,7659 |
| c | sklearn MLPClassifier (256) + BirdNET | 0,8000 | 0,6858 |
| d | Model produksi (numpy MLP) + threshold per spesies | 0,7800 | 0,6776 |

Mayoritas (a) sengaja rendah karena selalu menebak _negative. Hasil yang perlu dibaca hati-hati: pada subset stratified ini, LogisticRegression (b) dan sklearn MLP (c) mendapat test_acc lebih tinggi (0,88 dan 0,80) dibanding model produksi (d) 0,78. Ini bukan berarti model numpy lebih buruk, melainkan subset stratified max-3 per kelas memberi keseimbangan kelas yang sangat menguntungkan model linear dan sklearn MLP; pada data lapangan dengan dominasi kelas target tertentu dan ketidak-seimbangan yang lebih kuat, model produksi dengan threshold per spesies lebih cocok. Perbandingan apples-to-apples pada uji penuh 127 (lihat `ml/reports/metrics.json`) menunjukkan model produksi test_acc 0,6929 dan macro F1 0,6609, sudah terukur dengan threshold per spesies yang konsisten dengan aplikasi.

## 10.12 Ablation kontribusi komponen

Empat konfigurasi diuji pada subset stratified yang sama (50 dari 127 jendela uji, max 3 per kelas) supaya perbandingan antar konfigurasi konsisten:

| # | Konfigurasi | test_acc | macro_F1 |
|---|-------------|----------|----------|
| a | BirdNET embedding + normalisasi + threshold (model produksi) | 0,7200 | 0,6478 |
| b | Tanpa embedding: log-Mel 128-bin + MLP 256 | 0,2400 | 0,1551 |
| c | Tanpa normalisasi: embedding mentah + threshold | 0,5000 | 0,4633 |
| d | Tanpa threshold: argmax saja | 0,7800 | 0,6736 |

Selisih antara (a) dan (b) menunjukkan kontribusi BirdNET embedding sebagai fitur: akurasi turun ~0,48. Selisih antara (a) dan (c) menunjukkan kontribusi z-score: akurasi turun ~0,22 karena logits tanpa normalisasi meledak. Selisih antara (a) dan (d) menunjukkan kontribusi threshold per spesies: perbedaan tipis, jadi threshold terutama menyaring deteksi, bukan menaikkan akurasi top-1.

Subset 50 klip (bukan 127) demi kecepatan. Angka tidak dibandingkan langsung dengan uji penuh 127 karena subset berbeda; perbandingan antar konfigurasi pada subset identik yang konsisten.

## 10.13 Kurva pelatihan

Model dilatih ulang dengan seed tetap 42 selama 100 epoch (hidden 256, lr 0,001, tanpa augmentasi) untuk menggambarkan tren konvergensi pada subset validasi. Train loss turun cepat dan train accuracy mendekati 1,000; validation accuracy naik dari 0 ke ~0,55 dan best_val_acc pada run produksi setara 0,7244 (seed 2024). Pola train jauh di atas val mengindikasikan overfitting ringan, yang ditangani oleh dropout 0,3 dan weight decay 0,0001 pada model produksi final.

[Gambar 10: `docs/proposal/figures/fig12_train_history.png`]

## 10.14 ROC per spesies (One-vs-Rest)

ROC OvR dihitung untuk 26 kelas dan ditampilkan sebagai grid 6x5. AUC dipakai untuk audit: kelas dengan AUC di bawah 0,5 berarti lebih buruk dari tebakan acak; tidak ada kelas yang masuk kategori itu pada uji bersih saat ini. AUC terendah adalah Gallus gallus (0,667, support 1, support sangat kecil), Dicrurus macrocercus (0,796, support 3), Pycnonotus aurigaster (0,831, support 6); semua spesies selain _negative memiliki AUC di atas 0,65. Tujuh belas spesies mencapai AUC di atas 0,90, dan kelas _negative sendiri 0,808.

[Gambar 11: `docs/proposal/figures/fig13_roc_per_species.png`]

## 10.15 Snapshot test model

Snapshot test menjaga agar prediksi model tidak bergeser tanpa sengaja. Sepuluh klip gold dari test set (tersebar di 10 kelas berbeda) sudah disalin ke `ml/tests/snapshot_audio/` dan disimpan sebagai fixture di `apps/api/tests/fixtures/model_snapshots.json`. Fixture berisi embedding BirdNET 1024-dim, label, dan confidence untuk tiap klip. Test ini dijalankan pada saat training ulang model, pembaruan threshold, atau perubahan architecture; drift confidence di atas toleransi 0,10 dianggap perlu investigasi.

Tolerance 0,10 dipilih untuk mencakup beda float lintas Python (3,11 di container vs 3,12 di host) dan beda urutan reduce numpy pada logits. Untuk drift di atas 0,10, fixture perlu diregenerasi lewat `python ml/build_snapshot.py`.

# 11. Batasan Hasil Pengukuran

1. Angka mutu berasal dari klip arsip Xeno-canto dan korpus turunan, bukan dari rekaman hutan yang dikumpulkan sendiri. Rekaman lapangan asli belum ada.
2. Model lokal spesifik pada 25 spesies target. Spesies endemik regional yang tidak terwakili di data latih akan kurang dikenali.
3. Angka lokalisasi berasal dari rekaman buatan yang belum memuat gema, pantulan, dan kicauan bertumpuk seperti subuh di hutan. Angka tersebut adalah batas atas mutu, bukan perkiraan kinerja lapangan.
4. Triangulasi antar perangkat membutuhkan jam yang tersinkron. Tanpa itu selisih waktu tiba antar perangkat tidak sah.
5. Latensi hanya diukur pada CPU komputer pengembang.
6. Support per spesies kecil, sehingga angka per spesies bergerak kuat ketika satu klip berubah.
7. Akurasi 0,69 terukur pada kondisi simulasi berskala bersih; angka ini adalah batas atas mutu, bukan janji kinerja lapangan.
8. Tangga degradasi simulasi bukan pengukuran lapangan. Angka pada audio nyata akan berbeda.

# 12. Kesimpulan dan Rencana Lanjutan

GemaHutan menyediakan alur lengkap dari rekaman suara sampai laporan pemantauan, dengan dua jalur deteksi, verifikasi ahli yang tertutup kembali ke data latih, indeks akustik lanskap, dan perkiraan arah datang suara. Seluruh fitur yang diklaim pada proposal ini dapat dibuktikan dengan perintah di dalam repositori: 67 test API, 25 test worker, 3 snapshot test model, 28 pemeriksaan fitur, dan 6 pemeriksaan keamanan, semuanya lulus pada versi yang diserahkan.

Rencana lanjutan sesuai prioritas lapangan:

1. Mengumpulkan 30 sampai 50 menit rekaman lapangan sendiri (lima rekaman masing-masing enam menit pada waktu kicau pagi) dan memvalidasi sampel deteksinya lewat fitur verifikasi di aplikasi.
2. Memasang URL publik beserta basis data dan berkas lokalnya, dengan pendaftaran akun ditutup dan kata sandi contoh diganti.
3. Memperluas jumlah spesies target di luar 25 spesies, dengan memakai hasil verifikasi lapangan sebagai bahan latih tambahan.
4. Menerbitkan package Python `pip install gemahutan-ml` untuk peneliti yang ingin melatih ulang atau mengevaluasi model lokal tanpa setup repo lengkap.
5. Membangun aplikasi Android opsional untuk capture lapangan dengan antrean offline dan resume upload.

# 13. Daftar Pustaka

1. Boelman, N. T., Asner, G. P., Hart, P. J., dan Martin, R. E. (2007). Multi-trophic invasion resistance in Hawaii: bioacoustics, field surveys, and airborne remote sensing. *Ecological Applications*.
2. Kahl, S., Wood, C. M., Eibl, M., dan Klinck, H. (2021). BirdNET: A deep learning solution for avian diversity monitoring. *Ecological Informatics*, 61, 101236.
3. Kahl, S., et al. (2022). *BirdNET-Analyzer* (Versi 2.4) [Perangkat lunak]. K. Lisa Yang Center for Conservation Bioacoustics, Cornell University.
4. Kasten, E. P., Gage, S. H., Fox, J., dan Joo, W. (2012). The remote environmental acoustic laboratory's acoustic library. *Ecological Informatics*.
5. Knapp, C. H., dan Carter, G. C. (1976). The generalized correlation method for estimation of time delay. *IEEE Transactions on Acoustics, Speech, and Signal Processing*.
6. McFee, B., et al. (2015). librosa: Audio and music signal analysis in Python. *Proceedings of the 14th Python in Science Conference*.
7. Sueur, J., Pavoine, S., Hamerlynck, O., dan Duvail, S. (2008). Rapid acoustic survey for biodiversity appraisal. *PLoS ONE*, 3(12), e4065.
8. Ullrich, K., Schlüter, J., dan Grill, T. (2014). *scikit-maad* [Perangkat lunak].
9. ISO/IEC 25010:2023. *Systems and software engineering. Systems and software Quality Requirements and Evaluation (SQuaRE). Product quality model*. Jenewa: ISO.
10. Pressman, R. S., dan Maxim, B. R. (2020). *Software Engineering: A Practitioner's Approach* (edisi ke-9). McGraw-Hill.
11. Sommerville, I. (2021). *Software Engineering* (edisi ke-11). Pearson.
12. W3C. (2023). *Web Content Accessibility Guidelines (WCAG) 2.2*. W3C Recommendation.
13. PostgreSQL Global Development Group. *PostgreSQL 16 Documentation*. https://www.postgresql.org/docs/
14. PostGIS Project. *PostGIS Manual*. https://postgis.net/documentation/
15. FastAPI. *Documentation*. https://fastapi.tiangolo.com
16. Vercel. *Next.js Documentation*. https://nextjs.org/docs
17. MapLibre. *MapLibre GL JS Documentation*. https://maplibre.org/maplibre-gl-js/docs/
18. Xeno-canto Foundation. *Xeno-canto: berbagi suara burung dari seluruh dunia*. https://xeno-canto.org
19. iNaturalist. California Academy of Sciences. https://www.inaturalist.org
20. MinIO. *MinIO Documentation*. https://min.io/docs/
21. Colvin, S. *arq: Fast job queues and RPC in python with asyncio*. https://github.com/python-arq/arq
22. OpenStreetMap contributors. *OpenStreetMap*. https://www.openstreetmap.org

# 14. Lampiran

- Lampiran A: Tabel metrik per spesies lengkap (precision, recall, F1, support, threshold) untuk 26 kelas, terdapat di `ml/reports/metrics.json` dan `ml/reports/thresholds.json`.
- Lampiran B: Daftar 44 method endpoint pada 36 path, terdapat di `docs/API.md` dan `docs/MANUAL.md` bagian 12.
- Lampiran C: Konfigurasi pelatihan (seed 42, epoch 300, hidden 256, lr 0,001), terdapat di `ml/train.py`.
- Lampiran D: Catatan verifikasi tiap angka klaim, terdapat di `docs/proposal/catatan-verifikasi.md`.

