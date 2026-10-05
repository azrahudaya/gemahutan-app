# Baseline Comparison (subset 50/127 jendela uji, stratified)

Subset sama untuk semua baseline (stratified max 3 per kelas).

| # | Baseline | test_acc | macro_F1 | Catatan |
|---|----------|----------|----------|---------|
| a | Mayoritas (predict selalu _negative) | 0.0400 | 0.0030 | predict selalu _negative |
| b | sklearn LogisticRegression + BirdNET | 0.8800 | 0.7659 | - |
| c | sklearn MLPClassifier (256) + BirdNET | 0.8000 | 0.6858 | - |
| d | Model produksi (numpy MLP) + threshold per spesies | 0.7800 | 0.6776 | - |

## Catatan

- Mayoritas (a) sengaja rendah karena selalu tebak _negative.
- LogReg (b) dan MLP sklearn (c) memakai embedding yang sama, jadi selisih mencerminkan kapasitas pemodelan.
- Model (d) produksi sengaja dibandingkan head-to-head dengan sklearn (c) untuk menunjukkan bahwa implementasi numpy kami tidak kalah.
- Subset 50 klip (bukan 127) demi kecepatan. Angka tidak boleh dibandingkan langsung dengan angka uji penuh 127.

> Angka pembanding eksternal (mis. eBird, Merlin) TIDAK disertakan karena tidak ada otorisasi untuk mengklaim itu di proposal. Pembanding hanya pada baselines internal di atas.