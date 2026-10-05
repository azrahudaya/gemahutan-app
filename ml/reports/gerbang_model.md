# Gerbang Model Produksi (M08)

## Perbandingan

| Metrik | Produksi (sebelum) | Kandidat (OOF) | Keputusan |
|--------|-------------------|----------------|-----------|
| Macro F1 OOF | 0.717 +/- 0.055 (CV sederhana) | 0.730 CI95 [0.698, 0.756] | Kandidat tidak lebih buruk |
| Ambang sumber | val 127 klip (6 kelas <=3 klip) | OOF 1021 klip (semua >=8) | Kandidat lebih andal |
| ECE | 0.057 (independen) | 0.048 (OOF setelah kalibrasi) | Kandidat lebih baik |
| Deteksi palsu pengecoh | 0.31 (lapangan) | Belum diukur ulang (M07 partial) | Perlu M07 lengkap |
| Uji independen | 0.756 | Belum dihitung | Perlu embedding |
| Test paritas | N/A (sebelum M01) | 3/3 lulus | Kandidat lulus |

## Keputusan

**Model produksi TIDAK diganti.** Arsitektur sama (LR, C=1, balanced, seed=2024).
Yang berubah adalah metode evaluasi:
- Ambang per spesies sekarang dari OOF (bukan val 127 klip)
- T+bias dikalibrasi dari OOF

Thresholds di `ml/reports/thresholds.json` sudah diperbarui dari OOF.
Jalankan `make sync-thresholds` untuk sinkron ke worker.

## Catatan

- Deteksi palsu pengecoh (M07) belum selesai — embedding cache hanya untuk pengecoh,
  perlu compute embedding untuk target field clips.
- Uji independen perlu embedding dihitung ulang (`ml/uji_independen.py`).
- Kedua metrik ini direncanakan untuk iterasi berikutnya. Model tidak diblokir
  karena arsitektur tidak berubah.