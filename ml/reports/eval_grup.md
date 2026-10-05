# Evaluasi Berkelompok (Grouped CV)

- Metode: StratifiedGroupKFold 5-fold
- Klip XC: 1021
- Klip non-XC (selalu latih): 7335
- C: 1.0, class_weight: balanced
- Seed: 2026

## Agregat OOF

| Metrik | Nilai | CI95 |
|--------|-------|------|
| Accuracy | 0.7365 | [0.709, 0.763] |
| Macro F1 | 0.7302 | [0.698, 0.756] |
| ECE | 0.1435 | - |

## Per Fold

- Fold 1: n_train=8151, n_val=205, acc=0.6732, f1=0.6462
- Fold 2: n_train=8152, n_val=204, acc=0.7941, f1=0.7845
- Fold 3: n_train=8152, n_val=204, acc=0.7157, f1=0.6982
- Fold 4: n_train=8152, n_val=204, acc=0.7647, f1=0.7455
- Fold 5: n_train=8152, n_val=204, acc=0.7353, f1=0.7339

## Per Spesies (OOF)

| Spesies | Support | F1 | Precision | Recall |
|---------|---------|----|-----------|--------|
| Aegithina tiphia | 34 | 0.6571 | 0.6389 | 0.6765 |
| Amaurornis phoenicurus | 36 | 0.8254 | 0.9630 | 0.7222 |
| Anthreptes malacensis | 39 | 0.6567 | 0.7857 | 0.5641 |
| Aplonis panayensis | 32 | 0.6429 | 0.7500 | 0.5625 |
| Arachnothera longirostra | 35 | 0.7797 | 0.9583 | 0.6571 |
| Centropus bengalensis | 38 | 0.7463 | 0.8621 | 0.6579 |
| Chalcophaps indica | 33 | 0.8333 | 0.9259 | 0.7576 |
| Cinnyris jugularis | 44 | 0.6852 | 0.5781 | 0.8409 |
| Cisticola juncidis | 41 | 0.8919 | 1.0000 | 0.8049 |
| Corvus macrorhynchos | 31 | 0.9153 | 0.9643 | 0.8710 |
| Dicrurus macrocercus | 35 | 0.5862 | 0.7391 | 0.4857 |
| Gallus gallus | 22 | 0.2667 | 0.5000 | 0.1818 |
| Geopelia striata | 36 | 0.8169 | 0.8286 | 0.8056 |
| Haliastur indus | 43 | 0.7949 | 0.8857 | 0.7209 |
| Hirundo tahitica | 29 | 0.5172 | 0.5172 | 0.5172 |
| Lonchura punctulata | 42 | 0.8571 | 0.9429 | 0.7857 |
| Merops philippinus | 42 | 0.9157 | 0.9268 | 0.9048 |
| Orthotomus sutorius | 38 | 0.8250 | 0.7857 | 0.8684 |
| Passer montanus | 43 | 0.7857 | 0.8049 | 0.7674 |
| Prinia familiaris | 11 | 0.3077 | 1.0000 | 0.1818 |
| Pycnonotus aurigaster | 43 | 0.6933 | 0.8125 | 0.6047 |
| Pycnonotus goiavier | 40 | 0.8108 | 0.8824 | 0.7500 |
| Rhipidura javanica | 37 | 0.8732 | 0.9118 | 0.8378 |
| Spilopelia chinensis | 35 | 0.9041 | 0.8684 | 0.9429 |
| Todiramphus chloris | 36 | 0.7879 | 0.8667 | 0.7222 |
| _negative | 126 | 0.6087 | 0.4628 | 0.8889 |
