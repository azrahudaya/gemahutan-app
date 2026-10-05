# Hasil Negatif (eksperimen yang gagal / tidak menaikkan mutu)

Dokumen ini memenuhi syarat ML_00 bagian 6: status MELESET hanya sah kalau
semua eksperimen wajib terdokumentasi di sini. Ditulis 29 Sep 2026.

## 1. Kandidat v5: negatif iNat diganti negatif Xeno-canto

**Perubahan tunggal**: korpus v3 yang 3.205 negatif iNat diganti 1.482 negatif
XC (237 spesies non-target, lisensi terbukti non-ND). Val dan uji tidak berubah.

**Korpus**: v3 8.356 -> v5 6.633 klip (train 6.379, val 127, uji 127).

**Hasil**:

| Metrik | v3 (produksi) | v5 (kandidat) | Selisih |
|---|---|---|---|
| Akurasi split uji (pool sama, norm masing-masing) | 0,7795 | 0,7638 | -0,0157 |
| CV bersarang F1 (pool v5) | 0,7288 (pool v3) | 0,6939 | metode/pool beda, tidak sebanding langsung |
| Spesies turun recall > 0,15 | - | 3 | - |

Catatan B1: CV v3 dan v5 dihitung pada pool berbeda (v5 menghapus 3.205
negatif). Angka F1 CV tidak boleh diklaim "naik/turun" tanpa menyamakan pool.

**Tiga spesies turun** (masing-masing turun 1 klip, support kecil):

| Spesies | Support uji | v3 | v5 | Selisih |
|---|---|---|---|---|
| Amaurornis phoenicurus | 5 | 1,000 | 0,800 | -0,200 |
| Cinnyris jugularis | 6 | 1,000 | 0,833 | -0,167 |
| Pycnonotus goiavier | 6 | 1,000 | 0,833 | -0,167 |

Support 5-6 klip berarti satu klip menggeser 0,167-0,200. Jadi penurunan ini
ekuivalen satu klip per spesies, di dalam derau. Namun kriteria gerbang
"tidak ada spesies turun recall > 0,15" tetap TIDAK terpenuhi secara literal.

**Kesimpulan**: v5 TIDAK lulus gerbang. Produksi tetap LR v3. Dua sebab yang
mungkin: (a) jumlah negatif v5 lebih sedikit (3.927 lawan 5.650), (b) unduhan
XC burung hanya mencapai 237 spesies / 1.482 klip, di bawah target 300 spesies
/ 2.647 klip pengganti, sehingga keragaman negatif kurang.

**Yang tetap dicapai**: korpus v5 punya lisensi yang bisa dibuktikan per klip
(non-ND), menjawab masalah data C17, meski mutunya belum menang.

## 2. Unduhan negatif non-burung gagal

Target: 558 klip pengganti iNat serangga/mamalia (belalang + kelelawar, maks 600).

**Hasil**: 1 klip (xc-873854) sebelum dihentikan.

**Sebab**: rekaman belalang/kelelawar XC berupa WAV 96 kHz stereo (puluhan MB).
Setelah unduhan massal 1.482 klip burung, Xeno-canto membatasi laju unduhan
ke sekitar 11 KB/s sehingga satu berkas memerlukan puluhan menit. Kandidat
non-burung juga sedikit: `grp:grasshoppers` Indonesia 23 spesies,
`grp:bats` 3 spesies.

**Status**: tidak dipaksakan (sesuai instruksi). Dicatat berapa yang didapat.

## 3. Sapuan konfigurasi cascade: hanya satu parameter berpengaruh

**C13 open-set, putaran 1** (`ml/reports/sapu_cascade.md`):

| Parameter | Pengaruh pada metrik e2e |
|---|---|
| `trackb_wajib_birdnet` (on/off) | BESAR: deteksi palsu 44% -> 21,6% |
| `ambang_birdnet_nontarget` (0,05-0,3) | TIDAK ADA (identik) |
| `margin_top1_top2` (0-0,2) | TIDAK ADA (identik) |

Sebab: metrik e2e menghitung spesies target, dan deteksi palsu pengecoh berasal
dari Track B (classifier lokal), bukan dari BirdNET non-target.

**Putaran 2** (`ml/reports/sapu_cascade2.md`, seluruh data):

| Parameter | Pengaruh |
|---|---|
| `min_kemunculan_ulang` 2->4 | kecil: deteksi palsu 21,6% -> 20,6% |
| `ambang_kuat` 0,5->0,7 | sedang: 21,6% -> 18,6% (recall phone turun) |
| `min_durasi_s` 1,0->2,0 | TIDAK ADA (identik) |

**Putaran 3** (subset pilih, `ml/reports/sapu_cascade_v3.md`):

| Konfigurasi | P | R | DetPalsu | PhoneP | PhoneR |
|---|---|---|---|---|---|
| baseline | 0,624 | 0,798 | 0,424 | 0,830 | 0,696 |
| wajib-bn | 0,798 | 0,644 | 0,203 | 0,919 | 0,607 |
| kuat06 | 0,812 | 0,625 | 0,186 | 0,919 | 0,607 |
| kuat07 | 0,818 | 0,606 | 0,170 | 0,914 | 0,571 |

**Belum ada konfigurasi yang menembus target** (deteksi palsu <= 0,15, phone
P >= 0,75, phone R >= 0,62). Konfirmasi BirdNET menaikkan presisi besar tapi
menurunkan recall target di bawah syarat. Skor energi dan pooling beberapa
jendela belum dicoba.

**Akar**: classifier Track B salah klasifikasi spesies non-target dengan
keyakinan tinggi. Ini bukan kedipan lemah yang bisa ditapis ambang; butuh
data negatif. Kandidat v5 mengganti sumber negatif (iNat -> XC), tetapi deteksi
palsu v5 tidak pernah diukur saat putaran ML_06 pertama. Angka akurasi split uji
saja tidak cukup untuk menyimpulkan efek terhadap deteksi palsu. Setelah diukur
di A1 ML_07, v5 GAGAL G2-2 (FP lapor naik 21 -> 28).

## Eksperimen wajib yang masih belum dikerjakan

- C13: skor energi (`pakai_energi`), kombinasi terbaik setelah gerbang.
- C14: pemilihan jendela bersuara (skrip siap, belum dijalankan penuh),
  data spesies lemah, pooling beberapa jendela, MLP kecil.
- C15: kebijakan open-set terbaik di ponsel, analisis kesalahan iNat.
- C16: thread TFLite 1/2/4, batch segmen (sebagian: satu invoke sudah terbukti).