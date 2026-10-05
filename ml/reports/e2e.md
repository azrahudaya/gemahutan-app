# Evaluasi end-to-end (baseline produksi)

Dijalankan 27 Sep 2026 malam. Jalur `CascadeEngine.predict` (produksi,
termasuk penyaring). Cache BirdNET per berkas di `ml/data/cache_e2e/`.

## Perintah

```
TF_CPP_MIN_LOG_LEVEL=3 python3 ml/evaluasi_e2e.py
```

## Korpus

| Korpus | Berkas | Isi |
|--------|--------|-----|
| field/inat | 67 | rekaman ponsel iNaturalist, spesies target |
| field/xc_noisy | 108 | Xeno-canto kualitas C-E, spesies target |
| field/other | 97 | pengecoh (spesies non-target), label = [] |
| uji_independen | 98 | 131 klip negara lain (yang berlabel di manifest) |

Total 370 berkas berlabel. 148 berkas uji independen tanpa label di manifest
dilewati (tidak bisa dievaluasi tanpa ground truth).

## Agregat

| Metrik | Nilai |
|--------|-------|
| Presisi | 0,6172 |
| Recall | 0,7619 |
| Spesies non-target per berkas | 0,8324 |

## Deteksi palsu pengecoh (field/other)

Dihitung dari 97 berkas pengecoh. Detail per korpus di `e2e.json`.

## Catatan

Angka agregat dihitung ulang dari `per_berkas` dan cocok persis dengan laporan
(selisih 0,0000), diverifikasi oleh `ops/audit_model.py` C11.

Ini BASELINE produksi. Perbaikan model (penolakan spesies tak dikenal,
pemilihan jendela latih, data 4 spesies lemah) belum masuk dan akan dikerjakan
setelah baseline end-to-end ini lolos audit.