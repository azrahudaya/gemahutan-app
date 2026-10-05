# Evaluation Report -- GemaHutan Embedding Classifier (Track B)

## Overview

| Metric | Value |
|--------|-------|
| Test accuracy | 0.7402 |
| Val accuracy | 0.7717 |
| Macro precision | 0.7397 |
| Macro recall | 0.6582 |
| Macro F1 | 0.6764 |
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
| Aegithina tiphia | 0.6000 | 0.6000 | 0.6000 | 0.6100 | 5 |
| Amaurornis phoenicurus | 0.7500 | 0.6000 | 0.6667 | 0.6711 | 5 |
| Anthreptes malacensis | 1.0000 | 1.0000 | 1.0000 | 0.8000 | 5 |
| Aplonis panayensis | 0.5000 | 0.2500 | 0.3333 | 0.3686 | 4 |
| Arachnothera longirostra | 0.7500 | 1.0000 | 0.8571 | 0.6667 | 3 |
| Centropus bengalensis | 1.0000 | 0.8000 | 0.8889 | 0.6222 | 5 |
| Chalcophaps indica | 1.0000 | 1.0000 | 1.0000 | 0.6667 | 3 |
| Cinnyris jugularis | 0.7500 | 1.0000 | 0.8571 | 0.8333 | 6 |
| Cisticola juncidis | 1.0000 | 0.8333 | 0.9091 | 0.7436 | 6 |
| Corvus macrorhynchos | 1.0000 | 0.7500 | 0.8571 | 0.7500 | 4 |
| Dicrurus macrocercus | 0.0000 | 0.0000 | 0.0000 | 0.2303 | 3 |
| Gallus gallus | 0.0000 | 0.0000 | 0.0000 | 0.0312 | 1 |
| Geopelia striata | 1.0000 | 0.6000 | 0.7500 | 0.4929 | 5 |
| Haliastur indus | 0.6000 | 0.7500 | 0.6667 | 0.5284 | 4 |
| Hirundo tahitica | 1.0000 | 0.3333 | 0.5000 | 0.4000 | 3 |
| Lonchura punctulata | 1.0000 | 0.5000 | 0.6667 | 0.3333 | 4 |
| Merops philippinus | 1.0000 | 1.0000 | 1.0000 | 0.7500 | 4 |
| Orthotomus sutorius | 0.6000 | 0.6000 | 0.6000 | 0.6762 | 5 |
| Passer montanus | 0.7143 | 0.8333 | 0.7692 | 0.7917 | 6 |
| Prinia familiaris | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1 |
| Pycnonotus aurigaster | 0.6667 | 0.3333 | 0.4444 | 0.4646 | 6 |
| Pycnonotus goiavier | 1.0000 | 0.8333 | 0.9091 | 0.8095 | 6 |
| Rhipidura javanica | 1.0000 | 0.7500 | 0.8571 | 0.5167 | 4 |
| Spilopelia chinensis | 0.8000 | 0.8000 | 0.8000 | 0.6667 | 5 |
| Todiramphus chloris | 1.0000 | 1.0000 | 1.0000 | 0.8000 | 5 |
| _negative | 0.5000 | 0.9474 | 0.6545 | 0.7030 | 19 |

## Calibrated Thresholds (dari validation set)

| Species | Threshold |
|---------|-----------|
| Aegithina tiphia | 0.85 |
| Amaurornis phoenicurus | 0.45 |
| Anthreptes malacensis | 0.1 |
| Aplonis panayensis | 0.25 |
| Arachnothera longirostra | 0.2 |
| Centropus bengalensis | 0.3 |
| Chalcophaps indica | 0.1 |
| Cinnyris jugularis | 0.55 |
| Cisticola juncidis | 0.1 |
| Corvus macrorhynchos | 0.1 |
| Dicrurus macrocercus | 0.15 |
| Gallus gallus | 0.5 |
| Geopelia striata | 0.4 |
| Haliastur indus | 0.15 |
| Hirundo tahitica | 0.15 |
| Lonchura punctulata | 0.1 |
| Merops philippinus | 0.25 |
| Orthotomus sutorius | 0.1 |
| Passer montanus | 0.1 |
| Prinia familiaris | 0.25 |
| Pycnonotus aurigaster | 0.15 |
| Pycnonotus goiavier | 0.15 |
| Rhipidura javanica | 0.25 |
| Spilopelia chinensis | 0.25 |
| Todiramphus chloris | 0.15 |
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
