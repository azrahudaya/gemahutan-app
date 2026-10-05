# Status Lampiran 1

Dijalankan 27 Sep 2026 malam.

## Tabel A01-A06

| ID | Status | Perintah | Keluaran |
|----|--------|----------|----------|
| A01 | LULUS | Perbaiki _prediksi di test_model_snapshot.py: matmul manual x@W1+b1, ReLU, W2+b2, kalibrasi. Fixture tidak dibangun ulang. | test_snapshot_predict PASS, TOL 1e-3 |
| A02 | LULUS | Perbaiki 5 error ruff (variabel l, unused import) | ruff check = All checks passed |
| A03 | LULUS | evaluasi_grup.get_groups baca recordings[].rec. Test: 0 klip XC jatuh ke fallback | test_evaluasi_grup.py 2/2 PASS |
| A04 | LULUS | resep.py normalisasi=produksi reproduksi 0,7795. _fit_bias salin dari latih_produksi.py (gradient descent). | selisih 0,0000 |
| A05 | LULUS | E03 non-XC selalu di latih. Cek A4: grup terbesar 4,4%. Kalibrasi group-aware. | Lihat eval_bersarang.md |
| A06 | LULUS | E03 penuh dijalankan. CV 5-fold bersarang, bootstrap CI95, output di-commit. | eval_bersarang.json + .md |

## Keluaran CI terakhir

```
ruff check: All checks passed
pytest ml/tests: 15 passed
worker tests: 31 passed, 3 warnings
api tests: 97 passed, 3 skipped, 1 warning
```

## Angka E03 baru vs CV lama

| Metrik | CV lama (1021 XC, tanpa non-XC) | CV baru (894 XC + 7335 non-XC) |
|--------|------|------|
| Acc | 0,737 [0,709, 0,763] | 0,739 [0,724, 0,752] |
| F1 macro | 0,730 [0,698, 0,756] | 0,715 [0,704, 0,728] |

F1 turun 0,015. Penyebab:
1. 7.335 non-XC ditambahkan ke latih, memperkaya variasi _negative
2. Normalisasi dari data latih lipatan (bukan checkpoints_v2)
3. CV lama hanya pakai XC; tidak apple-to-apple

## GAGAL / BLOCKED

Tidak ada. Semua butir A01-A06 lulus.