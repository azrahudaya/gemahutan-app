# Evaluation Report -- GemaHutan Embedding Classifier (Track B)

## Overview

| Metric | Value |
|--------|-------|
| Test accuracy | 0.7795 |
| Val accuracy | 0.8110 |
| Macro precision | 0.7429 |
| Macro recall | 0.6993 |
| Macro F1 | 0.7040 |
| Jumlah kelas | 26 |
| Dataset | Xeno-canto Indonesia, 8.356 klip audio, 25 spesies target plus 1 kelas negatif |
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
| Aegithina tiphia | 0.7500 | 0.6000 | 0.6667 | 0.5333 | 5 |
| Amaurornis phoenicurus | 1.0000 | 1.0000 | 1.0000 | 0.8000 | 5 |
| Anthreptes malacensis | 0.8333 | 1.0000 | 0.9091 | 0.8000 | 5 |
| Aplonis panayensis | 0.3333 | 0.5000 | 0.4000 | 0.3513 | 4 |
| Arachnothera longirostra | 0.7500 | 1.0000 | 0.8571 | 0.6667 | 3 |
| Centropus bengalensis | 1.0000 | 0.8000 | 0.8889 | 0.7667 | 5 |
| Chalcophaps indica | 1.0000 | 1.0000 | 1.0000 | 0.6667 | 3 |
| Cinnyris jugularis | 0.6667 | 1.0000 | 0.8000 | 0.8095 | 6 |
| Cisticola juncidis | 1.0000 | 0.6667 | 0.8000 | 0.7917 | 6 |
| Corvus macrorhynchos | 1.0000 | 1.0000 | 1.0000 | 0.7500 | 4 |
| Dicrurus macrocercus | 0.0000 | 0.0000 | 0.0000 | 0.3889 | 3 |
| Gallus gallus | 0.0000 | 0.0000 | 0.0000 | 0.0417 | 1 |
| Geopelia striata | 1.0000 | 0.6000 | 0.7500 | 0.6156 | 5 |
| Haliastur indus | 1.0000 | 0.7500 | 0.8571 | 0.6000 | 4 |
| Hirundo tahitica | 0.2000 | 0.3333 | 0.2500 | 0.2242 | 3 |
| Lonchura punctulata | 1.0000 | 0.5000 | 0.6667 | 0.6250 | 4 |
| Merops philippinus | 0.8000 | 1.0000 | 0.8889 | 0.7500 | 4 |
| Orthotomus sutorius | 0.6000 | 0.6000 | 0.6000 | 0.5922 | 5 |
| Passer montanus | 0.8333 | 0.8333 | 0.8333 | 0.7917 | 6 |
| Prinia familiaris | 0.0000 | 0.0000 | 0.0000 | 0.3333 | 1 |
| Pycnonotus aurigaster | 1.0000 | 0.5000 | 0.6667 | 0.5866 | 6 |
| Pycnonotus goiavier | 0.8571 | 1.0000 | 0.9231 | 0.8333 | 6 |
| Rhipidura javanica | 1.0000 | 0.7500 | 0.8571 | 0.7000 | 4 |
| Spilopelia chinensis | 1.0000 | 0.8000 | 0.8889 | 0.6526 | 5 |
| Todiramphus chloris | 1.0000 | 1.0000 | 1.0000 | 0.8000 | 5 |
| _negative | 0.6923 | 0.9474 | 0.8000 | 0.8145 | 19 |

## Calibrated Thresholds (dari validation set)

| Species | Threshold |
|---------|-----------|
| Aegithina tiphia | 0.5 |
| Amaurornis phoenicurus | 0.15 |
| Anthreptes malacensis | 0.25 |
| Aplonis panayensis | 0.15 |
| Arachnothera longirostra | 0.15 |
| Centropus bengalensis | 0.15 |
| Chalcophaps indica | 0.1 |
| Cinnyris jugularis | 0.45 |
| Cisticola juncidis | 0.15 |
| Corvus macrorhynchos | 0.3 |
| Dicrurus macrocercus | 0.15 |
| Gallus gallus | 0.1 |
| Geopelia striata | 0.15 |
| Haliastur indus | 0.15 |
| Hirundo tahitica | 0.1 |
| Lonchura punctulata | 0.25 |
| Merops philippinus | 0.15 |
| Orthotomus sutorius | 0.15 |
| Passer montanus | 0.15 |
| Prinia familiaris | 0.1 |
| Pycnonotus aurigaster | 0.25 |
| Pycnonotus goiavier | 0.35 |
| Rhipidura javanica | 0.6 |
| Spilopelia chinensis | 0.35 |
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
