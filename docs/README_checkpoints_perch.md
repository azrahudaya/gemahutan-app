# gemahutan-checkpoints-perch

Classifier GemaHutan yang dilatih di atas embedding Perch 2.0, beserta laporan evaluasinya.

Model ini menggantikan BirdNET sebagai penghasil embedding, sedangkan arsitektur classifier-nya tetap sama: MLP 1536 ke 256 ke 26.

## Isi

| Berkas | Isi |
|---|---|
| `checkpoints_perch/best_model.npz` | bobot MLP 1536 ke 256 ke 26, plus temperature dan bias kalibrasi |
| `checkpoints_perch/normalization.npz` | mean dan std 1536 dimensi |
| `checkpoints_perch/temperature.json` | rincian kalibrasi vector scaling |
| `checkpoints_perch/meta.json` | epoch terbaik, akurasi, ukuran data latih |
| `reports_perch/metrics.json` | akurasi uji dan metrik per kelas |
| `reports_perch/metrik_per_kelas.json` | precision, recall, F1, support per kelas |
| `reports_perch/riwayat.json` | riwayat latih per epoch |
| `field_metrics_perch.json` | evaluasi korpus lapangan |

## Konfigurasi latih

| Parameter | Nilai |
|---|---|
| Embedding | Perch 2.0, 1536 dimensi, jendela 5 detik pada 32 kHz |
| Korpus | v2, 8258 klip |
| Latih / validasi / uji | 5392 / 127 / 127 |
| Negatif dipakai | 3000 dari 5650 |
| Bobot kelas | tidak dipakai, semua 1 |
| Epoch maksimum | 300, berhenti di 49, terbaik di 19 |
| Hidden | 256 |
| Seed | 2024 |

## Angka uji

Split uji adalah 127 klip lama yang sama, tidak diubah, supaya bisa dibandingkan.

| Kondisi | BirdNET produksi | BirdNET korpus v2 | Perch korpus v2 |
|---|---|---|---|
| Uji bersih | 0,6142 | 0,7323 | 0,8346 |
| Uji bersih tanpa ND | 0,6850 | 0,7402 | belum diukur |
| Rekaman ponsel iNaturalist | 0,4869 | 0,4607 | 0,6280 |
| Xeno-canto berisik | 0,6625 | 0,6687 | 0,7661 |
| Deteksi palsu pada pengecoh | 0,6484 | 0,5625 | 0,5094 |
| F1 makro | 0,5756 | 0,6755 | 0,7916 |
| Best val acc | 0,6693 | 0,7559 | 0,8661 |

## Sebaran antar seed

| Metrik | Rata-rata | Simpangan | Terendah | Tertinggi |
|---|---|---|---|---|
| Akurasi uji | 0,8399 | 0,0037 | 0,8346 | 0,8425 |
| F1 makro | 0,7832 | 0,0110 | 0,7677 | 0,7916 |
| Recall negatif | 1,0000 | 0,0000 | 1,0000 | 1,0000 |

Recall kelas negatif sempurna di ketiga seed. Artinya model menolak seluruh jendela pengecoh yang diuji, sedangkan deteksi palsu pada korpus lapangan tercatat 0,5094.

## Cara memakai

```bash
.venv-perch/bin/python3 ml/data/extract_perch.py \
  --manifest ml/data/manifest_v2.csv --out-dir ml/embeddings_perch

.venv/bin/python3 ml/train_v2.py \
  --emb-dir ml/embeddings_perch --splits ml/data/splits_v2.json \
  --epochs 300 --class-weight none --maks-negatif 3000 \
  --out-dir ml/checkpoints_perch --report-dir ml/reports_perch
```

## Syarat menjalankan

- Perch 2.0 wajib CUDA. Dengan TensorFlow CPU gagal dengan pesan "The current platform CPU is not among the platforms required by the module: [CUDA]".
- Venv terpisah `.venv-perch` berisi `tensorflow[and-cuda]==2.20.*`. Venv utama tetap memakai TensorFlow CPU untuk BirdNET.
- Terukur jalan di RTX 3050 6 GB dengan pemakaian VRAM 4.169 MB.

## Batasan

- Perch dijalankan lokal, sedangkan aplikasi produksi melayani permintaan pengguna. GPU lokal tidak selalu tersedia di server, jadi pemakaian di produksi perlu dihitung ulang biayanya.
- Split uji hanya 127 klip, jadi satu klip setara 0,8 poin.
- Deteksi palsu 0,5094 masih tinggi.
- Rekaman lapangan asli hasil rekaman sendiri belum ada.
- Tiga berkas MP3 korpus punya header rusak dan diselamatkan lewat ffmpeg, dua di antaranya hampir sunyi.

## Repo ini privat

Data latihnya berlisensi CC BY-NC-SA dan CC BY-NC, artinya pemakaian komersial tidak diizinkan. Lisensi model Perch sendiri Apache 2.0.
