# PROPOSAL

## GemaHutan: Pemantauan Biodiversitas Hutan Indonesia Berbasis Bioakustik

**JENIS LOMBA**

Software Development

**DISUSUN OLEH: TIM GEMAHUTAN**

Artya Epriliani, NPM 10124205 (ketua)
Azra Hudaya, NPM 50423244

**UNIVERSITAS GUNADARMA**
**2026**

---

## 1. Judul dan Nama Perangkat Lunak

Nama perangkat lunak: **GemaHutan**.

GemaHutan adalah aplikasi web pemantauan biodiversitas yang mengubah rekaman suara
hutan menjadi daftar deteksi spesies burung beserta waktu kejadian, lokasi, arah datang
suara, dan indeks akustik lanskap. Rekaman dapat diunggah dari telepon seluler, perekam
otomatis, atau direkam langsung dari peramban.

## 2. Latar Belakang Ide Perangkat Lunak

Indonesia termasuk negara dengan kekayaan burung terbesar di dunia, dan sebagian besar
spesiesnya hidup di hutan yang terus tertekan oleh pembukaan lahan, kebakaran, dan
perubahan tata guna. Menjaga kekayaan itu menuntut data yang rutin, sehingga perubahan
komunitas burung terdeteksi sebelum menjadi kerusakan yang mahal dipulihkan. Persoalannya,
data seperti itu mahal dikumpulkan. Survei lapangan membutuhkan pengamat berpengalaman,
perjalanan ke lokasi yang sering sulit dijangkau, dan waktu berjam-jam untuk mencatat
perjumpaan visual. Akibatnya banyak kawasan dipantau sekali setahun, atau hanya ketika ada
laporan kerusakan.

Suara menawarkan jalan lain. Burung yang jarang terlihat tetap terdengar, dan satu
perekam yang ditinggal selama beberapa hari dapat mengumpulkan puluhan jam audio dari
satu titik. Persoalannya bergeser dari pengumpulan menjadi penyaringan: mendengarkan
puluhan jam audio secara manual sama beratnya dengan survei visual. Di sinilah klasifikasi
otomatis bekerja, dan sejak BirdNET-Analyzer tersedia, model akustik yang cukup baik dapat
dijalankan sendiri tanpa pusat data besar.

Model yang tersedia umum, dan itu menyisakan dua celah yang kami temui saat mencoba
memakainya langsung. Pertama, keluarannya berupa daftar spesies dalam radius luas, tanpa
perbedaan antara spesies yang memang menjadi sasaran pemantauan di satu kawasan dan
spesies yang kebetulan terdeteksi. Ambang keyakinan yang sama untuk semua spesies membuat
perbandingan antar kawasan tidak dapat dipercaya. Kedua, hasil model diperlakukan sebagai
kesimpulan akhir, padahal keluarannya masih berupa dugaan yang perlu diperiksa orang yang
mengenali suara setempat. Tanpa jejak pemeriksaan, tidak ada cara mengetahui seberapa
besar koreksi manusia terhadap keluaran model, dan tidak ada jalan memperbaiki model dari
kesalahan yang ditemukan.

GemaHutan dibangun untuk menutup kedua celah itu. Sistem menjalankan dua jalur deteksi
berdampingan: penjaring awal berspesies luas untuk menemukan kejadian bunyi, dan penilai
khusus 25 spesies Indonesia dengan ambang hasil kalibrasi per spesies. Setiap deteksi
dapat diperiksa petugas lapangan atau peneliti, dan hasil pemeriksaan itu dipakai kembali
sebagai bahan latih. Kami juga menguji seberapa jauh mutu model turun ketika audionya
kotor, karena rekaman lapangan tidak pernah sebersih rekaman yang dipakai melatih.

Kami menambahkan satu hal yang belum ada pada alat sejenis: perkiraan arah datang suara.
Bagi pengelola kawasan, mengetahui bahwa kicauan berasal dari sisi utara titik ukur
membantu menentukan di mana petugas harus memeriksa, walaupun arah itu tidak dapat
menggantikan penelusuran langsung.

Tema USB 2026 menyebut ekosistem digital yang inklusif dan berkelanjutan. GemaHutan
masuk pada bagian pemantauan lingkungan: alat yang membuat data biodiversitas dapat
dikumpulkan oleh petugas kawasan dengan peralatan sederhana, disimpan pada basis data
milik lembaganya sendiri, dan diperiksa oleh ahlinya.

## 3. Tujuan dan Manfaat

### 3.1 Tujuan

1. Membangun alur kerja lengkap dari unggahan rekaman sampai laporan, sehingga satu
   rekaman lapangan dapat diproses tanpa perangkat lunak lain di luar aplikasi.
2. Menyediakan dua jalur deteksi berdampingan: penjaring berspesies luas dan penilai
   25 spesies Indonesia dengan ambang keyakinan yang dikalibrasi per spesies.
3. Menyediakan mekanisme verifikasi oleh petugas lapangan dan peneliti, dan memakai
   hasil verifikasi sebagai bahan latih lanjutan.
4. Mengukur penurunan mutu deteksi pada audio yang terdegradasi (angin, hujan,
   kebisingan kota, jarak sumber) dan melaporkan angka itu apa adanya kepada pengguna.
5. Menghitung indeks akustik lanskap dan perkiraan arah datang suara sebagai informasi
   pendamping daftar spesies.

### 3.2 Manfaat

Untuk pengelola kawasan, GemaHutan menyediakan riwayat kejadian spesies per lokasi
beserta berkas audionya, sehingga klaim perubahan komunitas burung dapat ditelusuri
sampai rekaman aslinya. Untuk peneliti, sistem menyimpan hasil verifikasi sebagai data
berlabel yang dapat dipakai melatih model berikutnya, termasuk klip yang berasal dari
rekaman ponsel yang kotor. Untuk petugas lapangan, unggahan dapat dilakukan dari telepon
seluler tanpa perangkat tambahan, dan arah datang suara memberi petunjuk awal ke arah
mana pemeriksaan visual perlu dilakukan.

## 4. Batasan Perangkat Lunak

Bagian ini menyebut hal yang tidak dikerjakan atau belum dapat dijamin, supaya pengguna
tidak menyimpulkan lebih dari yang terukur.

1. Seluruh audio yang dipakai melatih dan menguji model berasal dari arsip Xeno-canto
   dan rekaman ponsel pada arsip publik iNaturalist. Rekaman lapangan yang kami kumpulkan
   sendiri belum ada, sehingga angka akurasi pada klip bersih adalah batas atas mutu.
2. Aplikasi tidak menentukan lokasi dari suara. Koordinat selalu berasal dari lokasi
   yang dipilih pengguna saat mengunggah, dan koordinat itu dipakai model untuk menyaring
   daftar spesies yang mungkin ada di wilayah tersebut.
3. Perkiraan arah datang suara membutuhkan rekaman sedikitnya dua kanal yang tersinkron
   dan geometri mikrofon yang diketahui. Satu mikrofon tidak dapat menentukan arah sama
   sekali, dan susunan mikrofon yang segaris tidak dapat memisahkan arah depan dari arah
   belakang.
4. Perkiraan jarak hanya dihitung kalau perangkat pernah dikalibrasi pada jarak dan level
   acuan. Tanpa kalibrasi, kolom jangkauan dibiarkan kosong, bukan diisi angka perkiraan.
5. Aplikasi ini alat bantu pemantauan, bukan pengganti survei ahli. Deteksi yang sudah
   diverifikasi tetap perlu ditafsirkan bersama data lapangan lain sebelum dipakai
   mengambil keputusan pengelolaan.
6. Aplikasi Android khusus dan alat baris perintah portabel belum dikerjakan. Aplikasi
   web sudah dapat dipasang sebagai PWA di layar utama telepon seluler.
7. Korpus audio yang berlisensi NoDerivatives tidak dipakai melatih maupun menguji model,
   karena pemotongan klip termasuk membuat karya turunan. Dari 1370 klip pada manifest
   awal, 446 klip berlisensi NoDerivatives dikeluarkan sebelum pelatihan.


## 5. Metodologi Pengembangan Perangkat Lunak

Pengembangan memakai pendekatan iteratif dengan siklus pendek: satu siklus menghasilkan
satu kelompok fitur yang dapat diuji, lalu diakhiri pengukuran sebelum fitur berikutnya
dibuka. Alasan pemilihan ini praktis. Kebutuhan aplikasi pemantauan tidak dapat
dirumuskan lengkap di depan, karena angka akurasi model baru diketahui setelah model
dijalankan dan diuji, dan angka itu mengubah keputusan berikutnya.

Setiap siklus menjalankan lima langkah berikut secara berurutan.

1. Perumusan kebutuhan dan kriteria terima. Setiap fitur ditulis bersama cara mengukurnya,
   misalnya "spektrogram tersimpan dan permintaan kedua memakai cache, dibuktikan dengan
   selisih waktu render pertama dan kedua".
2. Implementasi di repositori tunggal, dengan migrasi basis data yang selalu naik dan
   turun bersih.
3. Pengujian otomatis: test API, test worker, dan test antarmuka, ditambah pemeriksaan
   keamanan dan pemeriksaan fitur berbasis HTTP.
4. Pengukuran pada sistem yang benar-benar berjalan, memakai peramban sungguhan dan
   perekaman audio nyata, bukan simulasi di dalam kode.
5. Pencatatan hasil pengukuran dan keputusan desain pada berkas di dalam repositori,
   termasuk hasil yang negatif, supaya keputusan berikutnya tidak mengulang jalan buntu.

Penekanan pada langkah keempat dan kelima membedakan proyek ini dari sekadar prototipe.
Satu contoh pengaruh pengukuran terhadap desain: metode augmentasi data dicoba lebih dulu
daripada memperluas jumlah spesies, dan hasilnya negatif. Melatih model dari nol dengan
1951 klip simulasi menurunkan akurasi uji bersih dari 0,7795 menjadi 0,5862 karena model
menghafal pola derau simulasi. Karena itu model produksi dibiarkan memakai bobot semula,
dan angka kegagalan itu dilaporkan di aplikasi, bukan disimpan sebagai catatan internal.

Alat bantu pengembangan: Git untuk riwayat perubahan, Docker Compose untuk menjalankan
enam layanan (api, worker, db, redis, minio, web) dengan satu perintah, serta pemeriksaan
otomatis gaya penulisan kode dan tipe data pada setiap perubahan.

## 6. Analisis Kebutuhan dan Desain Solusi

### 6.1 Pengguna dan peran

Aplikasi membedakan tiga peran, dan pembedaan itu ditegakkan di sisi server. Menyembunyikan
tombol di antarmuka saja tidak cukup, karena permintaan yang dikirim langsung ke API harus
tetap ditolak.

| Peran | Kewenangan |
|---|---|
| Petugas lapangan (ranger) | Mengunggah rekaman, melihat daftar rekaman, deteksi, dan spesies |
| Peneliti (researcher) | Semua kewenangan petugas, ditambah verifikasi deteksi dan menjalankan ulang pemrosesan |
| Pengelola (admin) | Semua kewenangan peneliti, ditambah mengelola akun, lokasi, dan perangkat |

Kewenangan diperiksa di lapisan dependensi API untuk setiap permintaan. Uji otomatis
memastikan endpoint tulis perangkat dan endpoint akun menolak peran petugas dengan kode
403, dan tombol yang pasti ditolak tidak ditampilkan di antarmuka.

### 6.2 Kebutuhan fungsional utama

1. Unggah satu berkas audio atau unggah batch sampai 20 berkas sekaligus, dengan status
   dan pesan galat per berkas.
2. Perekaman langsung dari peramban memakai mikrofon perangkat.
3. Pemrosesan otomatis di latar belakang dengan indikator tahap dan persen kemajuan.
4. Deteksi spesies dengan keyakinan, rentang waktu kejadian, dan asal jalur deteksi.
5. Verifikasi deteksi oleh peneliti sebagai benar, salah, atau belum pasti.
6. Peta sebaran lokasi, dengan kerucut arah datang dan lingkaran perkiraan jangkauan
   kalau datanya tersedia.
7. Indeks akustik lanskap per rekaman.
8. Ekspor data rekaman dan ekspor deteksi terverifikasi dalam format CSV, serta halaman
   laporan siap cetak.
9. Manajemen perangkat, termasuk geometri mikrofon dan data kalibrasi.
10. Riwayat pemrosesan dan percobaan ulang otomatis maksimal tiga kali per rekaman.

### 6.3 Kebutuhan nonfungsional

Diambil dari karakteristik mutu ISO/IEC 25010 yang relevan untuk aplikasi pemantauan.

| Karakteristik | Target dan cara pembuktian |
|---|---|
| Kesesuaian fungsional | Pemeriksaan otomatis berbasis HTTP untuk seluruh fitur, 28 pemeriksaan, semua harus lulus |
| Keandalan | Percobaan ulang job maksimal tiga kali, status pekerjaan tidak tertinggal pada pemrosesan |
| Kinerja | Spektrogram memakai cache, render kedua di bawah 0,1 detik |
| Kemudahan pakai | Kontras teks memenuhi WCAG AA, target sentuh minimal 44 piksel, tanpa geser horizontal pada lebar 390 piksel |
| Keamanan | Endpoint data menolak akses tanpa token, kata sandi di-hash Argon2, sesi logout mencabut token di Redis, login dibatasi lima percobaan gagal per menit |
| Pemeliharaan | Test API 57, test worker 25, test antarmuka 51 |

### 6.4 Arsitektur solusi

Enam layanan berjalan terpisah di dalam jaringan lokal mesin pengembang maupun server.

- **web**: antarmuka Next.js, dirender di sisi server, diakses di port 3001.
- **api**: layanan FastAPI yang menangani autentikasi, unggahan, kueri data, ekspor, dan
  siaran status pekerjaan.
- **worker**: pemroses latar belakang berbasis Redis Queue yang menjalankan model dan
  menulis hasil ke basis data.
- **db**: PostgreSQL dengan ekstensi PostGIS untuk kolom geografis lokasi.
- **redis**: antrean pekerjaan, penghitung batas percobaan, dan penyimpanan daftar token
  yang sudah dicabut.
- **minio**: penyimpanan berkas audio dan cache spektrogram.

Alur satu rekaman, dari unggah sampai hasil: berkas masuk ke MinIO, baris rekaman dibuat
di basis data, pekerjaan dimasukkan ke antrean Redis, worker mengambil pekerjaan,
mengunduh audio, menyeragamkan format audio untuk model, menjalankan dua jalur deteksi,
menghitung indeks akustik, menyimpan spektrogram ke cache, dan menulis hasil ke basis
data. Sepanjang tahap itu worker menulis tahap dan persen kemajuan, yang diteruskan ke
peramban lewat siaran status sehingga pengguna melihat kemajuan tanpa memuat ulang
halaman.

[Gambar 1: fig01_alur_sistem.png]

### 6.5 Skema data

Basis data memuat tabel `users`, `sites`, `devices`, `species`, `recordings`,
`detections`, `acoustic_indices`, dan `jobs`. Beberapa keputusan skema yang perlu
disebut:

- Lokasi menyimpan koordinat pada kolom `geom` bertipe POINT dengan sistem rujukan 4326,
  sehingga kueri jarak dan sebaran dapat dilakukan langsung di basis data.
- Tabel `detections` menyimpan kolom hasil lokalisasi: `azimuth_deg`,
  `azimuth_confidence`, `azimuth_kembar_deg`, `range_m`, dan `localization_engine`.
  Kolom ini dibiarkan kosong kalau syarat pengukuran tidak terpenuhi, dan tidak pernah
  diisi nol karena nol derajat adalah arah yang sah.
- Tabel `species` menyimpan `default_threshold` per spesies dan penanda
  `model_supported` yang menandai 25 spesies yang punya kelas di penilai khusus.
- Rekaman menyimpan `batch_id` supaya unggahan batch dapat dipantau sebagai satu
  kelompok.
- Pekerjaan menyimpan `progress` dan `stage` supaya kemajuan dapat ditampilkan dan
  kegagalan dapat didiagnosis tanpa membaca log server.

Perubahan skema dikelola dengan Alembic. Setiap migrasi diuji naik, turun satu langkah,
lalu naik lagi sebelum digabungkan.


## 7. Implementasi Perangkat Lunak

### 7.1 Teknologi

| Bagian | Teknologi | Alasan pemilihan |
|---|---|---|
| Antarmuka | Next.js 14, TypeScript, Tailwind CSS, TanStack Query | Render sisi server mempercepat muat pertama, pengetikan statis menahan kesalahan data di peramban |
| Peta | MapLibre GL dengan ubin raster OpenStreetMap | Tidak memerlukan kunci API, sehingga pemasangan di lembaga kecil tidak menambah biaya |
| Layanan API | FastAPI, SQLAlchemy async, Pydantic | Pemeriksaan skema otomatis dan dokumentasi OpenAPI yang dapat dibaca mesin |
| Basis data | PostgreSQL 16 dengan PostGIS | Kueri geografis langsung di basis data |
| Antrean dan cache | Redis 7 | Antrean pekerjaan, penghitung percobaan, dan daftar token yang dicabut |
| Penyimpanan berkas | MinIO | Antarmuka yang sama dengan penyimpanan objek awan, dapat dijalankan di server sendiri |
| Pemrosesan audio | librosa, soundfile, ffmpeg, scikit-maad | Dekode berbagai format, penyeragaman ke 48 kHz satu kanal untuk model, dan indeks akustik |
| Model | BirdNET-Analyzer 2.4 dan MLP numpy 2 lapis | BirdNET sudah terbukti pada klasifikasi burung, MLP ringan cukup untuk 25 kelas |
| Antrean pekerja | Redis Queue (arq) | Ringan, terintegrasi dengan Redis yang sudah dipakai |

### 7.2 Dua jalur deteksi

Jalur A memakai BirdNET-Analyzer 2.4 secara langsung, dengan cakupan 6522 spesies
global. Perannya menemukan kejadian bunyi yang tidak terduga. Jalur B memakai embedding
BirdNET berdimensi 1024 yang dibekukan, lalu diklasifikasikan MLP dua lapis dengan
keluaran 25 spesies Indonesia ditambah satu kelas negatif. Perannya menaikkan ketepatan
pada spesies sasaran.

Keduanya dijalankan berurutan oleh satu mesin kaskade di dalam worker. Koordinat lokasi
diteruskan ke BirdNET sehingga daftar spesies yang dipertimbangkan menyempit ke wilayah
yang masuk akal, dan spesies dari wilayah lain dibuang. Ambang keyakinan tiap spesies
dibaca dari berkas hasil kalibrasi, dan ambang yang sama dipakai untuk menyaring
deteksi maupun untuk angka yang ditampilkan di halaman Spesies, sehingga tidak ada dua
angka berbeda untuk satu hal.

Kami juga menambahkan penyaring deteksi lemah: kejadian yang lebih pendek dari satu
detik dibuang, dan keyakinan di bawah 0,5 hanya diterima kalau muncul pada dua potongan
audio yang berbeda. Pada delapan klip demo, penyaring ini menurunkan jumlah deteksi dari
65 menjadi 38, dan yang dibuang memang deteksi berkeyakinan rendah (0,118 sampai 0,304)
sementara deteksi kuat (0,942 dan 0,804) tetap ada.

### 7.3 Data dan pelatihan

Dataset berasal dari arsip Xeno-canto untuk wilayah Indonesia: 1370 klip audio
mentah yang mencakup 25 spesies target. 446 klip berlisensi NoDerivatives
dikeluarkan sebelum persiapan data, sehingga dataset final berisi 8.356 klip
tanpa ND: 670 latih, 127 validasi, dan 127 uji.

Pelatihan memakai seed tetap 42, 300 epoch, 256 unit tersembunyi, dan laju pembelajaran
0,001. Nilai validasi terbaik 0,5433 dan akurasi data uji 0,5512. Seed ditulis karena
tanpa seed yang tetap, nilai validasi bergerak sekitar 0,05 antar proses dengan
konfigurasi yang sama, dan angka yang bergerak tidak dapat dipakai sebagai dasar
keputusan.

### 7.4 Indeks akustik lanskap

Setiap rekaman dihitung empat indeks: Acoustic Complexity Index, Normalized Difference
Soundscape Index, Acoustic Diversity Index, dan Bioacoustic Index. Perhitungan memakai
scikit-maad dan disimpan per rekaman. Indeks ini dipakai sebagai pembanding kondisi
lanskap antar lokasi dan antar waktu, terpisah dari pertanyaan spesies apa yang
terdeteksi.

### 7.5 Perkiraan arah datang suara

Arah datang dihitung dengan Generalized Cross-Correlation with Phase Transform antar
pasangan kanal. Selisih waktu tiba yang terukur dibandingkan dengan selisih waktu teori
untuk setiap sudut pada langkah 0,5 derajat, dan sudut dengan galat terkecil dipilih.
Geometri mikrofon disimpan per perangkat, sehingga kanal ke-i diketahui posisinya.

Satu hal yang kami temukan saat pengujian: susunan mikrofon yang segaris menghasilkan
pola selisih waktu yang sama untuk sudut cerminnya. Sudut 60 derajat dan 300 derajat
tidak dapat dipisahkan oleh susunan seperti itu. Awalnya perbedaan ini masuk hitungan
pembanding dan membuat nilai keyakinan arah jatuh mendekati nol walaupun azimuth yang
dihitung tepat, sehingga pengguna akan membaca hasil yang bagus sebagai kegagalan
pengukuran. Perbaikannya, sudut dengan pola selisih waktu identik dipisahkan dan
dilaporkan sebagai arah kembar pada kolom tersendiri. Antarmuka menampilkan keduanya,
misalnya "60 derajat, bisa juga 300 derajat", disertai keterangan bahwa susunan segaris
memang tidak memisahkan depan dan belakang.

Hasil pengukuran pada klip buatan dengan arah diketahui: galat arah median 0,0 derajat
pada SNR 30 sampai 5 dB dan 0,5 derajat pada SNR -5 dB untuk susunan empat mikrofon
bentang 0,5 m pada sumber 25 m. Pada klip demo empat kanal yang dibuat dari rekaman
nyata, azimuth terhitung 60,0 derajat dengan galat 0,00 derajat, keyakinan 0,58, dan
jangkauan dibiarkan kosong karena perangkatnya belum dikalibrasi.

[Gambar 9: fig09_lokalisasi.png]

### 7.6 Kemajuan pemrosesan dan siaran status

Worker menulis tahap dan persen kemajuan setelah setiap langkah: antre 0, unduh 10,
dekode 20, penjaringan 30 sampai 60, klasifikasi 60 sampai 75, lokalisasi 80, indeks 88,
spektrogram 96, dan selesai 100. Nilai ini disiarkan lewat endpoint Server-Sent Events,
dan peramban memakainya untuk memperbarui bilah kemajuan tanpa memuat ulang halaman.
Kalau siaran gagal, antarmuka berpindah ke pemuatan berkala tiap lima detik. Token
disiarkan lewat parameter kueri pada endpoint ini karena EventSource tidak dapat
mengirim header, dan batas itu dicatat di dokumentasi.

### 7.7 Keamanan

Kata sandi disimpan dengan Argon2. Login dibatasi lima percobaan gagal per surel dan
alamat IP per menit, dan dijawab 429 dengan header Retry-After. Logout mencabut token di
Redis sampai masa berlakunya habis, sehingga token yang sudah logout ditolak walau belum
kedaluwarsa. Seluruh endpoint data menolak permintaan tanpa token, dan itu diuji
otomatis untuk setiap endpoint. Enam pemeriksaan keamanan dijalankan sebelum demo:
endpoint data menolak tanpa token, logout mencabut token, login terkunci setelah
percobaan gagal berulang, port pengembangan terikat localhost, nilai rahasia bukan nilai
contoh, dan tidak ada kredensial di dalam repositori.

### 7.8 Pengujian dan operasi

| Jenis pengujian | Jumlah | Perintah |
|---|---|---|
| Test API | 57 lulus | `make test` |
| Test worker | 25 lulus | `make test-worker` |
| Test antarmuka | 51 lulus | `npx vitest run` di apps/web |
| Pemeriksaan fitur berbasis HTTP | 28 pemeriksaan lulus | `python3 ops/verify_features.py` |
| Pemeriksaan keamanan | 6 pemeriksaan lulus | `make security-check` |
| Uji klik menyeluruh | 24 langkah, 0 galat konsol | `python3 ops/e2e_clickthrough.py` |

Operasi pendukung: cadangan basis data dan berkas audio lewat `make backup` dengan
prosedur pemulihan yang diuji, tangkapan data demo, pemeriksaan kesehatan layanan, dan
integrasi berkelanjutan yang menjalankan test API, test worker, dan test antarmuka pada
setiap perubahan. Basis data uji dibersihkan otomatis setelah pengujian supaya data demo
tidak terisi akun dan perangkat hasil uji.

Perbaikan bug yang ditemukan lewat pengujian, dan itu menunjukkan nilai pengujian
berbasis sistem yang benar-benar berjalan: worker pernah memanggil operasi asinkron pada
sesi basis data yang sinkron, dan akibatnya bukan sekadar galat di log, melainkan semua
pekerjaan baru gagal dan rekaman tertinggal pada status pemrosesan. Bug seperti ini tidak
terlihat dari pengujian unit, dan sekarang dijaga oleh uji klik menyeluruh yang membaca
status akhir pekerjaan dari API.

### 7.9 Ukuran kinerja yang sudah diambil

| Pengukuran | Angka |
|---|---|
| Pemrosesan audio 19,4 detik pada CPU | 5,75 detik, sekitar 1,0 kali (belum diukur ulang) realtime |
| Render spektrogram pertama | 0,269 detik, sekitar 250 KB |
| Render spektrogram berikutnya | 0,049 detik dengan header cache hit |
| Geser horizontal pada lebar 390 piksel | 0 piksel pada lima halaman utama |
| Pelanggaran kontras WCAG | 0 dari pemeriksaan rumus kontras di delapan halaman |

## 8. Screenshot Mockup Antarmuka Perangkat Lunak

Antarmuka dirancang dengan arah visual hutan Indonesia: palet hijau sebagai warna utama,
latar gelap sebagai bawaan karena aplikasi dipakai di lapangan dan pada presentasi
panggung, ikon garis tipis yang konsisten, dan tata letak yang memuat data padat tanpa
kehilangan keterbacaan. Halaman yang tersedia:

1. Beranda perkenalan, `screenshots/01_landing.png`, menjelaskan fungsi aplikasi dan
   menuju halaman masuk.
2. Halaman masuk, `screenshots/02_login.png`, dengan pesan galat yang jelas untuk
   kredensial salah dan pembatasan percobaan.
3. Dasbor, `screenshots/03_dashboard.png`, memuat jumlah rekaman, spesies, deteksi, dan
   lokasi, grafik deteksi per hari, serta peta sebaran lokasi.
4. Halaman unggah, `screenshots/04_upload.png`, dengan pemilihan lokasi dan perangkat,
   unggahan banyak berkas sekaligus, serta riwayat batch beserta kemajuannya.
5. Daftar rekaman, `screenshots/05_daftar_rekaman.png`, dengan penyaring lokasi, spesies,
   status, rentang tanggal, dan bilah kemajuan pemrosesan per baris.
6. Detail rekaman, `screenshots/06_detail_rekaman.png`, memuat pemutar audio dengan
   gelombang suara, spektrogram, daftar deteksi, indeks akustik, dan tahap pemrosesan.
7. Daftar spesies, `screenshots/07_daftar_spesies.png`, memuat jumlah deteksi dan status
   konservasi, serta penanda apakah spesies termasuk 25 spesies yang dinilai penilai
   khusus.
8. Detail spesies, `screenshots/08_detail_spesies.png`, memuat ambang keyakinan yang
   dipakai pipeline, status IUCN, dan daftar deteksi terbaru.
9. Peta lokasi, `screenshots/09_lokasi.png`, dengan penanda tiap lokasi dan legenda
   bernomor supaya label tidak bertumpuk.
10. Detail lokasi, `screenshots/10_detail_lokasi.png`, memuat kerucut arah datang dan
    lingkaran perkiraan jangkauan kalau deteksi menyediakan datanya.
11. Dasbor pada lebar 390 piksel, `screenshots/11_dashboard_mobile.png`.
12. Detail rekaman pada lebar 390 piksel, `screenshots/12_detail_rekaman_mobile.png`.
13. Grafik deteksi per spesies, `screenshots/13_grafik_spesies.png`.

## 9. Dokumentasi Cara Penggunaan Perangkat Lunak

Petunjuk lengkap tersedia di dalam aplikasi pada halaman Dokumentasi, dan salinannya
disimpan di repositori sebagai `docs/MANUAL.md`. Ringkasannya:

1. **Menyalakan sistem.** Jalankan `make up` pada mesin yang sudah memasang Docker.
   Aplikasi terbuka pada `http://localhost:3001`, layanan API pada
   `http://localhost:8000`. Data contoh diisi dengan `make seed`, dan klip demo nyata
   dengan `make demo`.
2. **Masuk dan memilih peran.** Akun contoh disediakan untuk tiga peran. Peran petugas
   lapangan tidak melihat tombol tulis pada halaman Perangkat dan Pengguna karena API
   akan menolaknya.
3. **Menyiapkan lokasi.** Lokasi dibuat pada halaman Lokasi dengan nama, koordinat, dan
   deskripsi habitat. Koordinat ini dipakai model untuk menyaring daftar spesies.
4. **Menyiapkan perangkat.** Halaman Perangkat memuat nama, jenis, jumlah kanal, jarak
   antar mikrofon, dan data kalibrasi. Arah datang hanya dihitung kalau jarak antar
   mikrofon diisi, dan jangkauan hanya dihitung kalau data kalibrasi diisi.
5. **Mengunggah rekaman.** Satu berkas pada halaman Unggah, atau sampai 20 berkas
   sekaligus dengan nama batch. Format yang diterima wav, mp3, flac, ogg, m4a, aac,
   opus, dan webm, dengan batas 200 MB per berkas.
6. **Merekam dari peramban.** Halaman Rekam memakai mikrofon perangkat untuk merekam
   langsung dan mengunggahnya tanpa memindahkan berkas. Peramban akan meminta izin
   mikrofon pada kunjungan pertama.
7. **Memantau pemrosesan.** Kemajuan tampil pada daftar rekaman, detail rekaman, dan
   halaman batch. Kalau satu rekaman gagal, pesan galatnya tampil dan pemrosesan dapat
   diulang maksimal tiga kali.
8. **Memeriksa deteksi.** Pada detail rekaman, peneliti menandai setiap deteksi sebagai
   benar, salah, atau belum pasti. Hasil verifikasi dapat diekspor dan dipakai sebagai
   bahan latih lanjutan.
9. **Membaca arah dan jangkauan.** Kalau tersedia, panel deteksi menampilkan azimuth,
   arah mata angin, sudut kembar, dan perkiraan jangkauan. Kalau kosong, aplikasi
   menyebut alasan datanya tidak ada, bukan menampilkan angka kosong.
10. **Mengunduh dan melaporkan.** Ekspor CSV tersedia untuk daftar rekaman dan deteksi
    terverifikasi. Halaman Laporan menyusun ringkasan periode, spesies, dan lokasi yang
    siap dicetak menjadi PDF dari peramban.


## 10. Hasil dan Pembahasan

Seluruh angka pada bagian ini berasal dari berkas laporan di dalam repositori
(`ml/reports/`) dan dapat dihasilkan ulang dengan perintah yang tercatat di sana.

### 10.1 Mutu penilai khusus 25 spesies

| Metrik | Nilai |
|---|---|
| Akurasi data uji | 0,5512 |
| Akurasi validasi terbaik | 0,5433 |
| Presisi makro | 0,5389 |
| Recall makro | 0,5517 |
| F1 makro | 0,5239 |
| Jumlah kelas | 26 (25 spesies dan satu kelas negatif) |
| Pembagian data | 670 latih, 127 validasi, 127 uji (semua tanpa ND) |
| Temperature scaling | T=0,6972, NLL val turun dari 1,889 ke 1,606 (turun 15,01 persen, ECE 0,176 ke 0,071) |

[Gambar 2: fig02_f1_per_spesies.png]
[Gambar 3: fig03_precision_recall.png]
[Gambar 4: fig04_dataset.png]

Angka per spesies tidak dapat dibaca dengan bobot yang sama. Jumlah klip uji per spesies
hanya 3 sampai 8, sehingga satu klip menggeser nilai F1 sekitar 12 poin untuk support 8
dan sekitar 33 poin untuk support 3. Contohnya, Prinia familiaris memiliki F1 0,50 dengan
support hanya 3 klip, sementara Pycnonotus aurigaster dan Spilopelia chinensis mencapai
F1 1,00 dengan support 8 klip. Karena itu laporan menyebut support setiap spesies, dan
kami tidak memakai satu angka global untuk mengklaim mutu per spesies.

Perbandingan dua jalur deteksi:

| Aspek | Jalur A: BirdNET zero-shot | Jalur B: embedding dan MLP |
|---|---|---|
| Cakupan | 6522 spesies global | 25 spesies Indonesia |
| Data evaluasi | 274 klip uji Xeno-canto | 274 klip uji yang sama |
| Peran | penjaring awal di worker | penilai ulang dengan ambang per spesies |

### 10.2 Ambang per spesies

Ambang keyakinan tiap spesies dikalibrasi pada data validasi dan disimpan pada
`ml/reports/thresholds.json`. Nilainya berkisar 0,10 untuk Anthreptes malacensis sampai
0,60 untuk Prinia familiaris. Sebelum perbaikan, 23 dari 25 spesies menampilkan angka
berbeda di halaman Spesies dibanding angka yang dipakai pipeline. Sekarang satu skrip
penyelaras menyalin ambang ke basis data dan melaporkan nol selisih.

[Gambar 6: fig06_threshold.png]

### 10.3 Penurunan mutu pada audio terdegradasi

Kami membangun tangga degradasi delapan tingkat dari klip uji bersih. Gangguan
dibangkitkan menurut target rasio sinyal terhadap derau, bukan atenuasi desibel tetap,
karena desain desibel tetap membuat klip nyaris sunyi sehingga yang terukur adalah
keheningan, bukan jarak.

| Kondisi | Akurasi |
|---|---|
| Bersih (tanpa gangguan) | 0,7795 |
| Kontrol pengodean ulang | 0,6759 |
| Angin | 0,6250 |
| Hujan ringan | 0,6065 |
| Kebisingan kota | 0,5880 |
| Jarak 30 m | 0,5622 |
| Hujan deras | 0,5370 |
| Jarak 100 m | 0,5194 |
| Gabungan berat | 0,2817 |

Dua hal perlu dibaca dari tabel ini. Pertama, penurunan terbesar terjadi pada gabungan
gangguan, dan angka 0,2817 berarti model praktis tidak dapat dipakai pada kondisi
tersebut tanpa pendampingan. Kedua, kontrol pengodean ulang pun sudah turun sekitar 4
poin dari kondisi bersih, jadi sebagian penurunan berasal dari pemrosesan ulang berkas,
bukan dari gangguan fisik semata.

[Gambar 8: fig08_degradasi_audio.png]

### 10.4 Uji pada audio lapangan nyata

Korpus lapangan dibangun dari rekaman nyata, bukan simulasi: 108 klip Xeno-canto kualitas
C sampai E untuk wilayah Indonesia, 113 rekaman ponsel dari arsip iNaturalist, dan 21
klip pengecoh untuk mengukur deteksi palsu.

| Korpus | Akurasi |
|---|---|
| Xeno-canto kualitas C sampai E | 0,6594 |
| Rekaman ponsel iNaturalist | 0,5082 |
| Deteksi palsu pada klip pengecoh | 0,6172 |

Rekaman ponsel berada sekitar 21 poin di bawah klip bersih, dan itu angka yang paling
mendekati kondisi pemakaian sebenarnya di lapangan. Pada korpus yang sama kami menemukan
bahwa sebagian berkas dari ponsel tidak terbaca oleh pustaka analisis audio karena
berformat m4a dan aac. Sebelum fallback ffmpeg ditambahkan di tiga tempat, berkas seperti
itu dilewati diam-diam, dan laporan evaluasi hanya mencakup berkas yang kebetulan berformat
mp3. Laporan sekarang mencantumkan jumlah berkas terbaca dari total.

### 10.5 Eksperimen augmentasi data yang gagal

Kami menguji dua cara memasukkan kondisi lapangan ke data latih, dan keduanya tidak
memberi perbaikan yang layak dipakai.

| Cara | Hasil |
|---|---|
| Melatih dari nol dengan 1951 klip simulasi | Akurasi uji bersih turun ke 0,5862 karena model menghafal pola derau simulasi |
| Fine-tune dari bobot produksi | Menambah 0,5 sampai 2,8 poin pada kondisi simulasi, dan tidak menambah apa pun pada rekaman ponsel asli |

Karena itu model aplikasi tetap memakai bobot produksi, dan angka kegagalan ini
dilaporkan di halaman Model serta di laporan penelitian. Kami memilih melaporkannya
daripada menyembunyikannya, karena angka ini menjelaskan mengapa aplikasi tidak
menjanjikan peningkatan akurasi pada audio ponsel.

### 10.6 Indeks akustik lanskap

Empat indeks dihitung per rekaman dan dipakai membandingkan kondisi lanskap antar lokasi.

[Gambar 5: fig05_indeks_soundscape.png]

### 10.7 Perkiraan arah dan jangkauan

| Pengukuran | Hasil |
|---|---|
| Galat arah median, SNR 30 sampai 5 dB, bentang 0,5 m | 0,0 derajat, keyakinan 0,97 |
| Galat arah maksimum, SNR 0 dB | 1,0 derajat |
| Galat arah median, SNR -5 dB | 0,5 derajat, maksimum 3,5 derajat |
| Susunan bentang 1,2 m, SNR 20 sampai 0 dB | galat median 0,5 derajat, maksimum 2,0 derajat |
| Triangulasi dua perangkat berjarak 300 m, galat arah 3 derajat | meleset median 14,4 m, terburuk 56,0 m |
| Triangulasi tiga perangkat | meleset median 14,4 m, terburuk 27,2 m |

Perkiraan jarak dari penyusutan amplitudo sangat sensitif terhadap taksiran level sumber.
Setelah dikalibrasi pada jarak 10 m, kesalahan taksiran level 3 dB membuat sumber 10 m
terbaca 14,1 m, kesalahan 6 dB membuatnya terbaca 20,0 m, dan kesalahan 10 dB membuatnya
terbaca 31,6 m. Karena kepekaan itu, kolom jangkauan hanya diisi kalau perangkat
memiliki data kalibrasi, dan aplikasi menampilkan keterangan kalau datanya tidak ada.

### 10.8 Kinerja

Audio 19,4 detik diproses dalam 5,75 detik pada CPU, sekitar 1,0 kali (belum diukur ulang) realtime. Angka ini
diukur pada komputer pengembang, dan belum diukur pada telepon kelas bawah atau perekam
otomatis hemat daya, sehingga kami tidak mengklaim aplikasi ini berbiaya rendah untuk
perangkat tersebut. Spektrogram pertama memerlukan 0,269 detik dan permintaan berikutnya
0,049 detik karena hasilnya disimpan di cache penyimpanan objek.

[Gambar 7: fig07_peta_lokasi.png]

## 11. Batasan Hasil Pengukuran

1. Angka mutu berasal dari klip bersih dan klip lapangan yang dipanen dari arsip publik,
   bukan dari rekaman hutan yang kami kumpulkan sendiri. Rekaman lapangan asli belum ada.
2. Angka lokalisasi berasal dari rekaman buatan yang belum memuat gema, pantulan, dan
   kicauan bertumpuk seperti suasana subuh di hutan. Karena itu angka tersebut adalah
   batas atas mutu, bukan perkiraan kinerja lapangan.
3. Triangulasi antar perangkat membutuhkan jam yang tersinkron. Tanpa itu selisih waktu
   tiba antar perangkat tidak sah, dan perangkat yang tidak tersinkron tidak boleh
   dipakai bersama.
4. Latensi hanya diukur pada CPU komputer pengembang.
5. Jumlah klip uji per spesies kecil, sehingga angka per spesies bergerak kuat ketika
   satu klip berubah.

## 12. Kesimpulan dan Rencana Lanjutan

GemaHutan menyediakan alur lengkap dari rekaman suara sampai laporan pemantauan, dengan
dua jalur deteksi, verifikasi ahli yang menutup loop ke data latih, indeks akustik
lanskap, dan perkiraan arah datang suara. Seluruh fitur yang diklaim pada proposal ini
dapat dibuktikan dengan perintah di dalam repositori: 57 test API, 25 test worker, 51 test
antarmuka, 28 pemeriksaan fitur, dan 6 pemeriksaan keamanan, semuanya lulus pada versi
yang diserahkan.

Rencana lanjutan sesuai prioritas lapangan yang sudah disetujui:

1. Mengumpulkan 30 sampai 50 menit rekaman lapangan sendiri, misalnya lima rekaman
   masing-masing lima menit pada waktu kicau pagi, lalu memvalidasi sampel deteksinya
   lewat fitur verifikasi di aplikasi.
2. Memasang URL publik beserta basis data dan berkas lokalnya, dengan pendaftaran akun
   ditutup dan kata sandi contoh diganti.
3. Memperluas jumlah spesies target di luar 25 spesies, dengan memakai hasil verifikasi
   lapangan sebagai bahan latih tambahan.

## 13. Daftar Pustaka

1. Boelman, N. T., Asner, G. P., Hart, P. J., & Martin, R. E. (2007). Multi-trophic
   invasion resistance in Hawaii: bioacoustics, field surveys, and airborne remote
   sensing. *Ecological Applications*.
2. Kahl, S., Wood, C. M., Eibl, M., & Klinck, H. (2021). BirdNET: A deep learning
   solution for avian diversity monitoring. *Ecological Informatics*, 61, 101236.
3. Kahl, S., et al. (2022). *BirdNET-Analyzer* (Versi 2.4) [Perangkat lunak]. K. Lisa
   Yang Center for Conservation Bioacoustics, Cornell University.
4. Kasten, E. P., Gage, S. H., Fox, J., & Joo, W. (2012). The remote environmental
   assessment laboratory's acoustic library. *Ecological Informatics*.
5. Knapp, C. H., & Carter, G. C. (1976). The generalized correlation method for
   estimation of time delay. *IEEE Transactions on Acoustics, Speech, and Signal
   Processing*.
6. McFee, B., et al. (2015). librosa: Audio and music signal analysis in Python.
   *Proceedings of the 14th Python in Science Conference*.
7. Sueur, J., Pavoine, S., Hamerlynck, O., & Duvail, S. (2008). Rapid acoustic survey
   for biodiversity appraisal. *PLoS ONE*, 3(12), e4065.
8. Ullrich, K., Schlüter, J., & Grill, T. (2014). *scikit-maad* [Perangkat lunak].
9. ISO/IEC 25010:2023. *Systems and software engineering. Systems and software Quality
   Requirements and Evaluation (SQuaRE). Product quality model*. Jenewa: ISO.
10. Pressman, R. S., & Maxim, B. R. (2020). *Software Engineering: A Practitioner's
    Approach* (edisi ke-9). McGraw-Hill.
11. Sommerville, I. (2021). *Software Engineering* (edisi ke-11). Pearson.
12. W3C. (2023). *Web Content Accessibility Guidelines (WCAG) 2.2*. W3C Recommendation.
13. PostgreSQL Global Development Group. *PostgreSQL 16 Documentation*.
    https://www.postgresql.org/docs/
14. PostGIS Project. *PostGIS Manual*. https://postgis.net/documentation/
15. FastAPI. *Documentation*. https://fastapi.tiangolo.com
16. Vercel. *Next.js Documentation*. https://nextjs.org/docs
17. Xeno-canto Foundation. *Xeno-canto: berbagi suara burung dari seluruh dunia*.
    https://xeno-canto.org
18. iNaturalist. California Academy of Sciences. https://www.inaturalist.org
19. MinIO. *MinIO Documentation*. https://min.io/docs/
20. Colvin, S. *arq: Fast job queues and RPC in python with asyncio*.
    https://github.com/python-arq/arq
