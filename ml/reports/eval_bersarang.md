# Evaluasi bersarang (E03)

Dijalankan 27 Sep 2026 malam.

## Perintah

```
python3 ml/evaluasi_bersarang.py
```

## Desain pembagian data (A4)

Klip XC (894) dibagi 5 lipatan StratifiedGroupKFold per perekam.
Klip non-XC (7.335: iNat 3.205, sea-bird 3.124, ULM 1.006) selalu di latih.

| Lipatan | Latih XC | Latih non-XC | Uji XC | Uji non-XC |
|---------|----------|-------------|--------|-----------|
| 1       | 691      | 7.335       | 203    | 0         |
| 2       | 721      | 7.335       | 173    | 0         |
| 3       | 721      | 7.335       | 173    | 0         |
| 4       | 721      | 7.335       | 173    | 0         |
| 5       | 722      | 7.335       | 172    | 0         |

Grup perekam: 222 grup. Grup terbesar: David Darrell-Lambert 39 klip (4,4%).
Tidak ada grup > 10%. Pembagian memenuhi syarat A4.

## Hasil

| Metrik | Mean ± Std | CI95 |
|--------|-----------|------|
| Acc    | 0,739 ± 0,016 | [0,7245, 0,7523] |
| F1 macro | 0,715 ± 0,014 | [0,7043, 0,7277] |

ECE per lipatan: 0,064-0,127. Kalibrasi T per lipatan: 1,135-1,630.
C terbaik: 0,1 (4 dari 5 lipatan), 1,0 (1 lipatan).

## Perbandingan dengan CV lama

| Metrik | CV lama (1021 XC, tanpa non-XC) | CV baru (894 XC + 7335 non-XC) |
|--------|------|------|
| Acc    | 0,737 [0,709, 0,763] | 0,739 [0,724, 0,752] |
| F1 macro | 0,730 [0,698, 0,756] | 0,715 [0,704, 0,728] |

F1 turun 0,015. Penyebab:
1. Non-XC menambah 7.335 klip negatif ke latih, memperkaya variasi `_negative`.
   Model jadi lebih konservatif, menurunkan recall kelas langka.
2. Normalisasi dari data latih lipatan, bukan dari checkpoints_v2.
3. CV lama tidak memasukkan non-XC sama sekali; perbandingan tidak apple-to-apple.

## Output

- `ml/reports/eval_bersarang.json` -- agregat + per lipatan
- `ml/reports/evalb_per_spesies.json` -- per spesies (26 kelas)
- `ml/reports/eval_bersarang.md` -- laporan ini