# gemahutan-checkpoints-v2

Model classifier GemaHutan hasil latih pada korpus v2, beserta laporan evaluasinya.

## Isi

| Berkas | Isi |
|---|---|
| `checkpoints_v2/best_model.npz` | bobot MLP 1024 ke 256 ke 26, plus temperature dan bias kalibrasi |
| `checkpoints_v2/normalization.npz` | mean dan std 1024 dimensi |
| `checkpoints_v2/temperature.json` | rincian kalibrasi vector scaling |
| `checkpoints_v2/meta.json` | epoch terbaik, akurasi, ukuran data latih |
| `reports_v2/metrics.json` | akurasi uji dan metrik per kelas |
| `reports_v2/metrik_per_kelas.json` | precision, recall, F1, support per kelas |
| `reports_v2/riwayat.json` | riwayat latih per epoch |
| `reports_v2/training_history.png` | kurva train dan val |
| `field_eval_v2final.md` | evaluasi kondisi audio lapangan |
| `field_metrics_v2final.json` | angka evaluasi lapangan dalam bentuk mesin |

## Konfigurasi latih

| Parameter | Nilai |
|---|---|
| Korpus | v2, 8258 klip |
| Latih / validasi / uji | 5392 / 127 / 127 |
| Negatif dipakai | 3000 dari 5650 |
| Bobot kelas | tidak dipakai, semua 1 |
| Epoch maksimum | 300, berhenti di 55 |
| Hidden | 256 |
| Seed | 2024 |

## Angka uji

Split uji adalah 127 klip lama, tidak diubah, supaya bisa dibandingkan dengan model produksi sebelumnya.

| Kondisi | Model lama | Model ini |
|---|---|---|
| Uji bersih | 0,6142 | 0,7323 |
| Uji bersih tanpa ND | 0,6850 | 0,7402 |
| Rekaman ponsel iNaturalist | 0,4869 | 0,4607 |
| Xeno-canto berisik | 0,6625 | 0,6687 |
| Deteksi palsu pada pengecoh | 0,6484 | 0,5625 |

Semua angka diukur dengan skrip yang sama, `ml/evaluate_field.py`, memakai ambang dan pemotongan jendela yang sama seperti aplikasi.

## Sebaran antar seed

Konfigurasi yang sama dilatih dengan tiga seed.

| Metrik | Rata-rata | Simpangan | Terendah | Tertinggi |
|---|---|---|---|---|
| Akurasi uji | 0,7323 | 0,0170 | 0,7165 | 0,7559 |
| F1 makro | 0,6652 | 0,0097 | 0,6550 | 0,6783 |
| Recall negatif | 0,9825 | 0,0248 | 0,9474 | 1,0000 |

## Cara memakai

```bash
python3 ml/train_v2.py \
  --epochs 300 --class-weight none --maks-negatif 3000 \
  --out-dir ml/checkpoints_v2 --report-dir ml/reports_v2
```

Bobot kelas tidak dipakai karena pembobotan `balanced` pada korpus ini memberi kelas `_negative` bobot 0,055 dari total rasio 701 kali, sehingga kelas negatif praktis tidak terlatih dan recallnya hanya 0,105.

## Batasan

- Split uji hanya 127 klip, jadi satu klip bergerak sekitar 0,8 poin.
- Angka ponsel 0,4607 sedikit di bawah model lama yang 0,4869. Selisih itu sekitar 3 klip pada 610 jendela, jadi belum bisa disebut perbedaan nyata.
- Deteksi palsu 0,5625 masih tinggi. Turun dari 0,6484 tetapi belum selesai.
- Model mencapai akurasi latih 1,0000 pada epoch 4, jadi hafal data latih sejak awal. Validasi tetap naik perlahan sampai 0,7402 karena early stopping menahan epoch terburuk.
- Rekaman lapangan asli hasil rekaman sendiri belum ada, sehingga angka lapangan di sini masih dari arsip Xeno-canto dan iNaturalist.

## Repo ini privat

Data latihnya berlisensi CC BY-NC-SA dan CC BY-NC, artinya pemakaian komersial tidak diizinkan.
