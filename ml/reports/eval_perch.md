# Evaluation Report -- GemaHutan Embedding Classifier (Track B)

## Overview

| Metric | Value |
|--------|-------|
| Test accuracy | 0.8268 |
| Val accuracy | 0.8819 |
| Macro precision | 0.8274 |
| Macro recall | 0.7820 |
| Macro F1 | 0.7879 |
| Jumlah kelas | 26 |
| Dataset | Xeno-canto Indonesia, 924 klip audio, 25 spesies target plus 1 kelas negatif |
| Pembagian data | train 670, validasi 127, uji 127 klip |
| Embedding | BirdNET 1024-dim (GLOBAL_AVG_POOL), dibekukan |
| Classifier | MLP 2 lapis, numpy, seed tetap 42 |

> Angka di atas berasal dari latih ulang penuh dengan seed tetap
> (`python train.py --epochs 300 --hidden 256 --lr 0.001 --seed 42`), lalu
> `python evaluate.py`. Tanpa seed tetap, hasil antar run bervariasi sekitar
> 0.05 pada val_acc dengan konfigurasi yang sama, jadi selalu sebutkan seed
> saat membandingkan angka.
> Data uji dipisah per rekaman, bukan per potongan, supaya tidak ada kebocoran
> potongan dari rekaman yang sama ke data latih.

## Per-species Metrics (Test Set)

| Species | Precision | Recall | F1 | AUC-PR | Support |
|---------|-----------|--------|-----|--------|---------|
| Aegithina tiphia | 1.0000 | 0.6000 | 0.7500 | 0.6103 | 5 |
| Amaurornis phoenicurus | 1.0000 | 0.8000 | 0.8889 | 0.7667 | 5 |
| Anthreptes malacensis | 0.8333 | 1.0000 | 0.9091 | 0.8000 | 5 |
| Aplonis panayensis | 0.2000 | 0.2500 | 0.2222 | 0.1132 | 4 |
| Arachnothera longirostra | 1.0000 | 1.0000 | 1.0000 | 0.6667 | 3 |
| Centropus bengalensis | 0.5714 | 0.8000 | 0.6667 | 0.7250 | 5 |
| Chalcophaps indica | 1.0000 | 1.0000 | 1.0000 | 0.6667 | 3 |
| Cinnyris jugularis | 0.7500 | 1.0000 | 0.8571 | 0.8333 | 6 |
| Cisticola juncidis | 1.0000 | 0.5000 | 0.6667 | 0.8333 | 6 |
| Corvus macrorhynchos | 1.0000 | 1.0000 | 1.0000 | 0.7500 | 4 |
| Dicrurus macrocercus | 0.0000 | 0.0000 | 0.0000 | 0.2381 | 3 |
| Gallus gallus | 0.0000 | 0.0000 | 0.0000 | 0.5000 | 1 |
| Geopelia striata | 1.0000 | 0.8000 | 0.8889 | 0.8000 | 5 |
| Haliastur indus | 1.0000 | 0.5000 | 0.6667 | 0.7500 | 4 |
| Hirundo tahitica | 1.0000 | 1.0000 | 1.0000 | 0.6667 | 3 |
| Lonchura punctulata | 1.0000 | 0.5000 | 0.6667 | 0.4375 | 4 |
| Merops philippinus | 1.0000 | 1.0000 | 1.0000 | 0.7500 | 4 |
| Orthotomus sutorius | 1.0000 | 0.8000 | 0.8889 | 0.8000 | 5 |
| Passer montanus | 0.8571 | 1.0000 | 0.9231 | 0.8333 | 6 |
| Prinia familiaris | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 1 |
| Pycnonotus aurigaster | 1.0000 | 0.8333 | 0.9091 | 0.7778 | 6 |
| Pycnonotus goiavier | 1.0000 | 1.0000 | 1.0000 | 0.8333 | 6 |
| Rhipidura javanica | 0.8000 | 1.0000 | 0.8889 | 0.7500 | 4 |
| Spilopelia chinensis | 1.0000 | 1.0000 | 1.0000 | 0.8000 | 5 |
| Todiramphus chloris | 0.8333 | 1.0000 | 0.9091 | 0.8000 | 5 |
| _negative | 0.6667 | 0.9474 | 0.7826 | 0.8458 | 19 |

## Calibrated Thresholds (dari validation set)

| Species | Threshold |
|---------|-----------|
| Aegithina tiphia | 0.9 |
| Amaurornis phoenicurus | 0.15 |
| Anthreptes malacensis | 0.9 |
| Aplonis panayensis | 0.2 |
| Arachnothera longirostra | 0.1 |
| Centropus bengalensis | 0.2 |
| Chalcophaps indica | 0.1 |
| Cinnyris jugularis | 0.3 |
| Cisticola juncidis | 0.1 |
| Corvus macrorhynchos | 0.1 |
| Dicrurus macrocercus | 0.1 |
| Gallus gallus | 0.5 |
| Geopelia striata | 0.8 |
| Haliastur indus | 0.1 |
| Hirundo tahitica | 0.1 |
| Lonchura punctulata | 0.2 |
| Merops philippinus | 0.1 |
| Orthotomus sutorius | 0.1 |
| Passer montanus | 0.55 |
| Prinia familiaris | 0.15 |
| Pycnonotus aurigaster | 0.1 |
| Pycnonotus goiavier | 0.1 |
| Rhipidura javanica | 0.1 |
| Spilopelia chinensis | 0.2 |
| Todiramphus chloris | 0.1 |
| _negative | 0.3 |

## Track A vs Track B

| Metrik | Track A (BirdNET zero-shot) | Track B (Embedding + MLP) |
|--------|-----------------------------|---------------------------|
| Model | BirdNET-Analyzer v2.4 | Embedding BirdNET 1024-dim + MLP 2 lapis |
| Cakupan | 6522 spesies global | 25 spesies target Indonesia |
| Dataset evaluasi | 127 klip uji Xeno-canto | sama, 127 klip uji |
| Peran di aplikasi | penjaring awal di worker | penilai ulang untuk spesies lokal, threshold per spesies |

> Kedua track berjalan berdampingan di worker (CascadeEngine). Track A menjaga
> cakupan global, Track B menaikkan ketepatan pada spesies target dengan
> threshold hasil kalibrasi. Angka per spesies di atas adalah hasil evaluasi
> Track B pada klip uji yang tidak dipakai saat latih.
