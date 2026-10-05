# Ablation Study (subset 50/127 jendela uji, stratified)

Subset sama untuk semua konfigurasi: stratified max 3 klip per kelas, total 50 jendela. Subset ini yang dipakai konsisten.

| # | Konfigurasi | test_acc | macro_F1 |
|---|-------------|----------|----------|
| a | BirdNET embedding + normalisasi + threshold (model produksi) | 0.7200 | 0.6478 |
| b | Tanpa embedding BirdNET: log-Mel 128-bin + MLP 256 | 0.2400 | 0.1551 |
| c | Tanpa normalisasi: embedding mentah + threshold per spesies | 0.5000 | 0.4633 |
| d | Tanpa threshold: argmax saja, tanpa per spesies | 0.7800 | 0.6736 |

## Catatan

- Subset 50 klip (bukan 127) demi kecepatan. Angka tidak boleh dibandingkan langsung dengan angka uji penuh 127.
- Konfigurasi (b) melatih MLP kecil dari awal pada fitur log-Mel 128-dim, tanpa BirdNET, jadi wajar bila angkanya lebih rendah.
- Selisih antara (a) dan (d) menunjukkan efek threshold per spesies; selisih antara (a) dan (c) menunjukkan efek z-score.