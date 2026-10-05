# Formulir Uji Kegunaan GemaHutan (System Usability Scale)

Formulir ini dipakai untuk mengukur kegunaan aplikasi GemaHutan di https://gemahutan.site. Satu salinan
diisi untuk satu responden. Hasilnya masuk ke proposal (Bagian 5 dan Tabel 8).

Kuesioner memakai System Usability Scale (Brooke, 1996) versi bahasa Indonesia dari Sharfina dan Santoso
(2016), yang reliabilitasnya diukur dengan koefisien Alpha Cronbach 0,841. Kalimat pernyataan tidak boleh
diubah, karena perubahan kalimat membuat skor tidak lagi sebanding dengan penelitian lain. Yang dirapikan
hanya ejaan (misalnya "disistem" menjadi "di sistem").

---

## A. Panduan untuk pelaksana

Pelaksana adalah anggota tim yang mendampingi responden. Baca bagian ini sebelum sesi pertama.

**Persiapan**

1. Siapkan satu akun uji untuk setiap peran yang akan dicoba (admin, peneliti, *ranger*). Akun dibuat
   admin dari menu Pengguna. Jangan memakai akun pribadi tim.
2. Siapkan berkas audio contoh di perangkat responden: satu atau dua berkas dari folder
   `ml/demo_audio/` di kode sumber.
3. Pastikan perangkat terhubung ke internet dan peramban sudah terbuka di https://gemahutan.site.
4. Siapkan pengukur waktu (stopwatch di ponsel cukup).

**Selama sesi**

1. Bacakan bagian B (persetujuan) dan minta responden menyetujuinya.
2. Berikan skenario tugas di bagian D sesuai peran yang dicoba, satu per satu.
3. Jangan membantu dan jangan menunjuk tombol. Kalau responden macet lebih dari 2 menit atau
   meminta bantuan, berikan petunjuk singkat, lalu catat di kolom "Dibantu".
4. Responden boleh berpikir sambil berbicara. Catat ucapan penting di kolom catatan.
5. Setelah semua tugas selesai, berikan kuesioner di bagian E. Responden mengisi sendiri tanpa
   didampingi dan tanpa berdiskusi dengan pelaksana atau responden lain.
6. Terakhir, ajukan pertanyaan terbuka di bagian F.

**Hal yang tidak boleh dilakukan**

- Menjelaskan cara kerja aplikasi sebelum tugas dimulai.
- Mengarahkan jawaban kuesioner, misalnya dengan berkata "mudah, kan?".
- Mengisi kuesioner atas nama responden.
- Mengulang sesi dengan responden yang sama untuk memperbaiki skor.

**Durasi**: sekitar 15 sampai 20 menit per responden.

---

## B. Persetujuan responden

Dibacakan oleh pelaksana:

> Kami dari tim GemaHutan, Universitas Gunadarma, sedang menguji kegunaan aplikasi untuk lomba USB 2026.
> Yang diuji adalah aplikasinya, bukan kemampuan Anda. Anda akan diminta mengerjakan beberapa tugas, lalu
> mengisi 10 pernyataan singkat. Sesi ini memakan waktu sekitar 15 sampai 20 menit. Nama Anda tidak akan
> dicantumkan; di proposal hanya tertulis kode responden dan latar belakang umum. Anda boleh berhenti kapan
> saja tanpa alasan.

| | |
|---|---|
| Kode responden | R__ (diisi pelaksana, misalnya R01) |
| Responden bersedia ikut | ☐ Ya |
| Tanggal dan tempat | |
| Nama pelaksana | |

---

## C. Data responden

| Pertanyaan | Jawaban |
|---|---|
| Latar belakang | ☐ Mahasiswa kehutanan / biologi ☐ Petugas lapangan (*ranger*, polisi hutan, relawan) ☐ Anggota kelompok pecinta alam / pengamat burung ☐ Peneliti / dosen ☐ Lainnya: ______ |
| Instansi atau kelompok (boleh dikosongkan) | |
| Peran yang dicoba di aplikasi | ☐ *Ranger* ☐ Peneliti ☐ Admin |
| Perangkat yang dipakai | ☐ Ponsel ☐ Laptop / komputer |
| Peramban | ☐ Chrome ☐ Firefox ☐ Edge ☐ Safari ☐ Lainnya: ______ |
| Pernah memakai aplikasi pengenal suara burung (misalnya BirdNET)? | ☐ Ya ☐ Tidak |
| Pernah merekam suara satwa untuk keperluan kerja atau penelitian? | ☐ Ya ☐ Tidak |

---

## D. Skenario tugas

Kerjakan tugas sesuai peran yang dicoba. Pelaksana mengisi kolom hasil.

Keterangan kolom: **Selesai** diisi Ya atau Tidak. **Waktu** dalam menit dan detik. **Dibantu** diisi Ya
kalau pelaksana memberi petunjuk.

Kalau sebuah fitur belum tersedia di gemahutan.site saat sesi berlangsung, lewati tugas itu, tulis
"fitur belum tersedia" di kolom catatan, dan jangan menghitungnya sebagai gagal.

### D1. Peran *ranger* (dikerjakan di ponsel)

| No | Tugas yang dibacakan kepada responden | Selesai | Waktu | Dibantu | Catatan |
|---|---|---|---|---|---|
| 1 | Masuk ke aplikasi dengan akun yang sudah disiapkan. | | | | |
| 2 | Rekam suara di sekitar Anda selama sekitar 30 detik, lalu unggah rekaman itu. | | | | |
| 3 | Unggah satu berkas audio contoh yang sudah ada di ponsel. | | | | |
| 4 | Buka hasil rekaman yang baru Anda unggah, lalu sebutkan satu spesies yang terdeteksi beserta skornya. | | | | |
| 5 | Buka fitur simulasi lokasi. Pasang tiga alat virtual di peta, lalu tunjukkan perkiraan lokasi sumber suara. | | | | |

### D2. Peran peneliti (dikerjakan di laptop)

| No | Tugas yang dibacakan kepada responden | Selesai | Waktu | Dibantu | Catatan |
|---|---|---|---|---|---|
| 1 | Masuk ke aplikasi dengan akun yang sudah disiapkan. | | | | |
| 2 | Temukan rekaman terbaru, lalu putar potongan suara dari salah satu deteksinya. | | | | |
| 3 | Tandai tiga deteksi sesuai pendapat Anda: Benar, Salah, atau Ragu. | | | | |
| 4 | Unduh data deteksi yang sudah diverifikasi dalam format CSV. | | | | |
| 5 | Buka laporan bulanan, lalu sebutkan jumlah rekaman bulan ini. | | | | |

### D3. Peran admin (dikerjakan di laptop)

| No | Tugas yang dibacakan kepada responden | Selesai | Waktu | Dibantu | Catatan |
|---|---|---|---|---|---|
| 1 | Masuk ke aplikasi dengan akun yang sudah disiapkan. | | | | |
| 2 | Undang satu akun baru dengan peran *ranger* (pakai alamat surel yang diberikan pelaksana). | | | | |
| 3 | Tambahkan satu lokasi pemantauan baru beserta koordinatnya. | | | | |
| 4 | Tandai satu spesies sebagai spesies prioritas kawasan. | | | | |
| 5 | Buka dasbor, lalu sebutkan spesies yang paling sering terdeteksi. | | | | |

---

## E. Kuesioner System Usability Scale

Diisi sendiri oleh responden setelah semua tugas selesai.

Petunjuk untuk responden: beri tanda pada satu angka untuk setiap pernyataan. Isi semua pernyataan.
Kalau ragu, pilih angka 3. Jawab sesuai kesan pertama Anda, tidak perlu dipikirkan terlalu lama.
"Sistem ini" berarti aplikasi GemaHutan yang baru saja Anda pakai.

1 = Sangat tidak setuju, 2 = Tidak setuju, 3 = Netral, 4 = Setuju, 5 = Sangat setuju

| No | Pernyataan | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|---|
| 1 | Saya rasa saya akan sering menggunakan sistem ini. | ☐ | ☐ | ☐ | ☐ | ☐ |
| 2 | Saya temukan sistem ini tidak harus dibuat serumit ini. | ☐ | ☐ | ☐ | ☐ | ☐ |
| 3 | Saya rasa sistem ini mudah digunakan. | ☐ | ☐ | ☐ | ☐ | ☐ |
| 4 | Saya rasa saya akan membutuhkan bantuan dari teknisi untuk menggunakan sistem ini. | ☐ | ☐ | ☐ | ☐ | ☐ |
| 5 | Saya temukan beberapa fungsi di sistem ini sudah terintegrasi dengan baik. | ☐ | ☐ | ☐ | ☐ | ☐ |
| 6 | Saya rasa di sistem ini ada banyak ketidaksesuaian. | ☐ | ☐ | ☐ | ☐ | ☐ |
| 7 | Saya pikir ke depannya banyak orang akan mudah mempelajari sistem ini dengan cepat. | ☐ | ☐ | ☐ | ☐ | ☐ |
| 8 | Saya temukan sistem ini sangat sulit untuk digunakan. | ☐ | ☐ | ☐ | ☐ | ☐ |
| 9 | Saya sangat yakin untuk menggunakan sistem ini. | ☐ | ☐ | ☐ | ☐ | ☐ |
| 10 | Saya butuh belajar banyak hal sebelum saya memulai menggunakan sistem ini. | ☐ | ☐ | ☐ | ☐ | ☐ |

---

## F. Pertanyaan terbuka

Diajukan pelaksana setelah kuesioner. Jawaban dicatat sedekat mungkin dengan kata-kata responden.

1. Bagian mana yang paling membingungkan atau paling lambat dikerjakan?
2. Fitur apa yang paling berguna untuk pekerjaan Anda di lapangan atau di kantor?
3. Apa yang perlu ada supaya Anda mau memakai aplikasi ini dalam pekerjaan sehari-hari?

| No | Jawaban |
|---|---|
| 1 | |
| 2 | |
| 3 | |

---

## G. Cara menghitung skor (dikerjakan tim, bukan responden)

Langkah per responden (Brooke, 1996):

1. Pernyataan bernomor ganjil (1, 3, 5, 7, 9): kontribusi = jawaban − 1.
2. Pernyataan bernomor genap (2, 4, 6, 8, 10): kontribusi = 5 − jawaban.
3. Jumlahkan sepuluh kontribusi (hasilnya 0 sampai 40).
4. Skor SUS = jumlah × 2,5 (hasilnya 0 sampai 100).

Skor SUS bukan persentase. Skor 70 tidak berarti "70% pengguna puas".

Contoh: jawaban 4, 2, 4, 1, 4, 2, 5, 1, 4, 2 memberi kontribusi 3, 3, 3, 4, 3, 3, 4, 4, 3, 3. Jumlahnya 33,
jadi skor SUS = 33 × 2,5 = 82,5.

Skor aplikasi adalah **rata-rata** skor SUS semua responden. Laporkan juga jumlah responden, skor terendah,
dan skor tertinggi.

**Tafsiran.** Bangor, Kortum dan Miller (2009) memetakan skor SUS ke skala ajektif berdasarkan rata-rata skor
untuk setiap kata sifat. Kategori ditentukan dari kata sifat yang rata-ratanya paling dekat dengan skor yang
diperoleh:

| Kata sifat | Rata-rata skor SUS |
|---|---|
| Worst imaginable (terburuk) | 12,5 |
| Awful (sangat buruk) | 20,3 |
| Poor (buruk) | 35,7 |
| OK (cukup) | 50,9 |
| Good (baik) | 71,4 |
| Excellent (sangat baik) | 85,5 |
| Best imaginable (terbaik) | 90,9 |

Catatan tim: nilai OK, Good, dan Excellent sudah dicocokkan dengan sumber yang mengutip Bangor, Kortum dan
Miller (2009). Nilai Worst imaginable, Awful, Poor, dan Best imaginable belum dicocokkan dengan naskah asli,
jadi periksa Tabel di naskah tersebut sebelum nilai itu dikutip di proposal.

**Catatan kejujuran.** Dengan 3 sampai 5 responden, skor SUS hanya memberi gambaran awal kegunaan, bukan angka
yang dapat digeneralisasi ke semua petugas konservasi. Proposal harus menuliskan jumlah dan latar responden
apa adanya.

---

## H. Rekap (diisi tim setelah semua sesi)

| Kode | Latar belakang | Peran dicoba | P1 | P2 | P3 | P4 | P5 | P6 | P7 | P8 | P9 | P10 | Skor SUS |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| R01 | | | | | | | | | | | | | |
| R02 | | | | | | | | | | | | | |
| R03 | | | | | | | | | | | | | |
| R04 | | | | | | | | | | | | | |
| R05 | | | | | | | | | | | | | |
| | | | | | | | | | | | | **Rata-rata** | |

| Ringkasan tugas | *Ranger* | Peneliti | Admin |
|---|---|---|---|
| Jumlah tugas selesai tanpa bantuan / total tugas | | | |
| Tugas yang paling sering gagal atau dibantu | | | |

Setelah tabel terisi, kirim isinya ke Claude. Skor, kategori, dan kalimat untuk Tabel 8 proposal akan
dihitung dari angka ini, tanpa diubah.

---

## Rujukan

- Bangor, A., Kortum, P. and Miller, J., 2009. Determining what individual SUS scores mean: Adding an adjective
  rating scale. *Journal of Usability Studies*, 4(3), pp. 114–123.
- Brooke, J., 1996. SUS: A "quick and dirty" usability scale. In: P.W. Jordan, B. Thomas, B.A. Weerdmeester
  and I.L. McClelland, eds. *Usability Evaluation in Industry*. London: Taylor & Francis, pp. 189–194.
- Sharfina, Z. and Santoso, H.B., 2016. An Indonesian adaptation of the System Usability Scale (SUS). In:
  *2016 International Conference on Advanced Computer Science and Information Systems (ICACSIS)*. IEEE,
  pp. 145–148. doi: 10.1109/ICACSIS.2016.7872776.
