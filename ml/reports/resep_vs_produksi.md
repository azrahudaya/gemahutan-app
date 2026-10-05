# resep.py vs latih_produksi.py: perbandingan langkah demi langkah

Dibandingkan 27 Sep 2026 malam.

## Ringkasan

| Langkah | `latih_produksi.py` (LR v3 produksi) | `resep.py` (sebelum A04) | `resep.py` (setelah A04) |
|---------|--------------------------------------|--------------------------|--------------------------|
| Normalisasi | `checkpoints_v2/normalization.npz` | data latih sendiri | mode `"produksi"` + `"lipatan"` |
| Batas negatif | 3000 | 3000 | 3000 |
| LogisticRegression | C=1.0, max_iter=3000, balanced | identik | identik |
| Fit temperature | grid 0.05-5.0 langkah 0.005 | grid 0.5-3.0 langkah 0.05 | grid 0.05-5.0 langkah 0.005 |
| Fit bias | gradient descent 2000 langkah lr=0.05 | **rumus analitik salah** `log(probs) - skor` | gradient descent 2000 langkah lr=0.05 |
| Acc produksi (terkalibrasi) | 0.7795 | 0.7165 | **0.7795** |
| Acc lipatan (terkalibrasi) | - | 0.7165 | **0.7638** |

## Akar masalah

`_fit_bias` versi lama (sebelum A04):

```python
bias[k] = mean(log(probs[mask,k]) - logits[mask,k] / T)
```

Rumus ini menghitung bias sebagai selisih log-probabilitas dan logits. Karena
log(probs) selalu negatif (probs < 1) dan logits bisa positif, selisihnya
menjadi negatif besar (-11 sampai -4). Hasilnya: semua logits digeser turun
drastis, softmax mendekati uniform, akurasi jatuh.

Perbaikan: salin `latih_bias` dari `latih_produksi.py` yang menggunakan
gradient descent 2000 langkah pada NLL. Ini menghasilkan bias yang teratur
dan AKURASI NAIK (0.748 -> 0.764 untuk mode lipatan).

## Mode normalisasi

- `normalisasi="produksi"` (BARU): mean/std dari checkpoint eksternal.
  Mereproduksi LR v3 persis: 0.7795, selisih 0.0000.
- `normalisasi="lipatan"`: mean/std di-fit dari data latih. Untuk CV
  di mana setiap lipatan punya data latih sendiri.

Perbedaan akurasi produksi vs lipatan: ~0.016 (0.7795 vs 0.7638). Ini
wajar karena normalisasi dari data latih lipatan berbeda distribusinya
dengan normalisasi dari korpus penuh (checkpoints_v2).