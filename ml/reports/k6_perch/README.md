# K6 Perch versus BirdNET pada pool yang sama persis

## Cara membandingkan

CV bersarang dijalankan dua kali dengan `--splits ml/data/splits_irisan_perch.json`
(klip yang punya embedding di kedua sisi). Pool terbukti identik:

| | n_xc | grup perekam | non_xc | kelas |
|---|---:|---:|---:|---:|
| Perch | 796 | 203 | 7306 | 26 |
| BirdNET v3 | 796 | 203 | 7306 | 26 |

Perbandingan pertama (Perch 796 vs BirdNET 894) dibuang karena tidak sebanding:
98 klip yang tidak punya embedding Perch SEMUANYA klip kelas langka, yaitu kelas
tersulit.

## Hasil

C14 mensyaratkan TIGA hal: F1 CV >= 0,78, CI bawah >= 0,75, DAN F1 uji
independen >= 0,75. Tabel ini hanya memuat dua yang pertama, jadi kolom
terakhirnya bukan status C14.

| Embedding | F1 CV | CI95 | Akurasi | Bagian CV C14 |
|---|---:|---|---:|---|
| BirdNET v3 (1024 dim) | 0,7340 | [0,6922, 0,7624] | 0,7588 | gagal |
| Perch (1536 dim) | 0,8386 | [0,7960, 0,8609] | 0,8643 | lulus |

Syarat ketiga (F1 independen) untuk Perch BELUM diketahui, bukan lulus: nol dari
135 klip uji independen punya embedding Perch saat tabel ini dibuat. Versi
sebelumnya menulis "C14 LULUS" di sini, dan itu koreksi di
`ml/reports/koreksi.md` butir putaran ML_10.

Selisih F1 +0,1046. Selang tidak tumpang tindih (Perch bawah 0,7960 di atas
BirdNET atas 0,7624), jadi perbedaannya nyata, bukan kebetulan sampel.

Per spesies: Perch menang di 22 dari 26 kelas, kalah di 2.

- Naik terbesar: Cinnyris jugularis 0,447 -> 0,895 (n=38), Prinia familiaris
  0,200 -> 0,500 (n=10), Anthreptes malacensis 0,588 -> 0,824 (n=34).
- Turun: Arachnothera longirostra 0,700 -> 0,600 (n=20), Spilopelia chinensis
  0,967 -> 0,900 (n=30).
- Gallus gallus tetap 0,111 (n=9). Embedding tidak menyelesaikan masalah data.

## Kenapa ini BELUM lulus gerbang G2

Empat hal yang belum ada, dan semuanya memblokir promosi:

1. **G2-4 tidak bisa dihitung.** Tidak satu pun dari 135 klip uji independen
   punya embedding Perch (0 dari 135). Gerbang mensyaratkan akurasi independen
   tidak turun > 0,03, dan itu tidak bisa dinilai tanpa ekstraksi ulang.
2. **C16 belum diukur.** ML_10 K6 mensyaratkan RAM dan latensi di bawah batas
   server 4 GB. Bobot Perch 410 MB plus embedding 1536 dim belum pernah diukur
   di jalur inferensi.
3. **Provenance embedding lemah.** `ml/embeddings_perch/` bertanggal 24
   September dari sesi lama, tanpa berkas meta atau params. Bobotnya
   (`ml/models_perch/`) TIDAK ADA di mesin ini, jadi hasilnya belum bisa
   direproduksi sekarang.
4. **Resep jendela berbeda.** `ml/data/extract_perch.py` memakai
   `DURASI_PERCH = 5.0` detik, sedangkan BirdNET 3,0 detik. Jadi selisih +0,1046
   mencampur dua hal: mutu embedding DAN panjang konteks audio. Untuk klaim
   "Perch lebih baik" yang bersih, salah satu harus disamakan.

## Yang sah dikatakan sekarang

Perch adalah satu-satunya komponen sepanjang putaran ini yang angkanya melewati
syarat C14, dan selisihnya terbukti nyata pada pool yang identik. Itu temuan
kuat dan layak dikejar.

Yang TIDAK sah: menyebut K6 lolos G2, atau memakai angka ini untuk promosi.
Butuh ekstraksi Perch untuk uji independen, pengukuran C16, dan penyamaan resep
jendela lebih dulu.
