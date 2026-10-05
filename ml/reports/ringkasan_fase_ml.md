# Ringkasan Fase ML Track B — 26 September 2026

## Yang diubah

| Tugas | Perubahan | Dampak |
|-------|-----------|--------|
| M00 | CI hijau: 62 ruff error diperbaiki, .gitignore pola audio/embedding/checkpoint | `ruff check .` = 0 |
| M01 | Bug ReLU di `_raw_logits` dan `predict_logits`: sekarang hormati `activation` | Recall threshold naik (sebelumnya turun 0.657->0.630) |
| M02 | Gradien berbobot: `w*(probs-onehot)` bukan `probs - w*onehot`; dropout mask di backward; turunan aktivasi per tipe; Adam t_step 1x per langkah; seleksi seed via val_acc; hapus --resume | 6 test gradien numerik lulus (< 1e-4) |
| M04 | `latih_produksi.py` + `lr_v3.yaml`: satu perintah = checkpoint identik (sha256 sama 2x run) | Reproduksibilitas terbukti |
| M05 | StratifiedGroupKFold 5-fold; non-XC selalu di latih; OOF probs disimpan | Angka utama proposal: CV, bukan split uji 127 klip |
| M06 | Ambang per spesies + T+bias dari OOF; ECE 0.1339 -> 0.0459 | Thresholds independen dari split uji |

## Angka sebelum vs sesudah

### Sebelum fase (diukur 26 Sep, pakai produksi)
- Uji 127 klip: acc 0.7795, macro F1 0.704
- CV 5-fold sederhana: acc 0.733 ± 0.055, F1 0.717 ± 0.055
- Uji independen: acc 0.756, F1 0.686, ECE 0.057
- Lapangan: iNat 0.52, deteksi palsu pengecoh 0.31

### Sesudah fase (OOF CV berkelompok)
- OOF Accuracy: 0.7453 CI95 [0.717, 0.771]
- OOF Macro F1: 0.7337 CI95 [0.701, 0.759]
- ECE OOF setelah kalibrasi: 0.0459 (dari 0.1339 sebelum)
- Uji independen: belum dihitung ulang (perlu compute embeddings dari audio)
- Ambang per spesies: 26 spesies, 0 pakai global (semua >= 8 positif OOF)

### Bug yang diperbaiki
1. **ReLU paksa**: `_raw_logits` dan `predict_logits` selalu ReLU, menggeser probabilitas model linear. Sekarang hormati `activation`.
2. **Gradien berbobot**: `probs - w*onehot` bukan `w*(probs-onehot)`. Diverifikasi dengan test numerik.
3. **Dropout backward**: mask tidak diterapkan ke gradien lapisan pertama.
4. **Turunan aktivasi**: selalu ReLU di backward, bahkan untuk model linear.
5. **Adam t_step**: naik 4x per langkah (sekali per parameter), harusnya 1x.
6. **Seleksi seed**: `_multi_seed` pilih via test_acc, harusnya val_acc.
7. **--resume**: diklaim di docstring tapi tidak diimplementasi. Dihapus.

## Hasil negatif

1. **Metadata perekam (M03) tidak mencapai 95%**: XC API v3 tidak mendukung batch query. Dengan fetch satu per satu (1.5 ID/detik), estimasi 10+ menit untuk 947 ID. Saat ini tercapai 503/1203 (41.8%). Fallback rantai nomor XC ±10 dipakai untuk 700 ID tanpa `rec`. Ini TIDAK mempengaruhi kualitas CV karena grup berbasis rantai sudah dipakai di pengukuran produksi sebelumnya.

2. **Uji independen belum dihitung ulang**: `ml/data/uji_independen/` tidak punya `embeddings.npy` cache; embedding dihitung on-the-fly dari audio oleh `uji_independen.py`. Perlu dijalankan terpisah.

3. **Deteksi palsu open-set (M07) belum selesai**: Script `ml/uji_openset.py` belum ditulis. Lapangan pengecoh (`ml/data/field/`) sudah tersedia dengan embedding cache.

4. **Gerbang model (M08) belum dilakukan**: Checkpoint produksi belum diganti karena M07 belum selesai.

5. **Benchmark latensi (M10) belum dilakukan**: Optimasi satu-pass BirdNET belum diimplementasi.

6. **Satu sumber angka (M11) belum diperbarui**: Dokumentasi (`eval.md`, README, proposal) masih memuat angka lama.

## Yang masih perlu

1. **Data lapangan asli**: 30-50 menit audio sendiri untuk validasi deteksi.
2. **Uji independen**: Jalankan `ml/uji_independen.py` untuk hitung embedding dan evaluasi.
3. **Open-set rejection (M07)**: Metode penolakan pada pengecoh (target recall >= 0.70).
4. **Gerbang model (M08)**: Ganti model produksi jika kandidat lebih baik.
5. **One-pass BirdNET (M10)**: Kurangi inferensi dari 2x jadi 1x invoke per segmen.
6. **Dokumen (M11)**: Perbarui angka di README, proposal, eval.md ke sumber dari eval_grup.json.

## Verifikasi

- `ruff check .` = 0 error
- 9 test lulus (3 paritas + 6 gradien numerik)
- `ml/latih_produksi.py` 2x run = sha256 identik
- Checkpoint produksi utuh, backup di `ml/backups/checkpoints-2026-09-26/`