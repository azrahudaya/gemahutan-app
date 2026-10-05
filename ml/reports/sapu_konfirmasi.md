# Sapuan konfirmasi BirdNET bertingkat (L6-3)

Baseline = paket produksi. Metrik dihitung HANYA dari bagian pilih.

| Konfigurasi | FP pilih | FP rate | Recall target | Phone P | Phone R | Waktu |
|---|---:|---:|---:|---:|---:|---:|
| tanpa_konfirmasi | 25/59 | 0.4237 | 0.7981 | 0.8298 | 0.6964 | 273.1s |
| wajib_bn_saja | 12/59 | 0.2034 | 0.6442 | 0.9189 | 0.6071 | 276.0s |
| topk_1 | 10/59 | 0.1695 | 0.625 | 0.9167 | 0.5893 | 274.4s |
| topk_3 | 10/59 | 0.1695 | 0.625 | 0.9167 | 0.5893 | 318.6s |
| topk_5 | 10/59 | 0.1695 | 0.625 | 0.9167 | 0.5893 | 324.1s |
| topk_10 | 10/59 | 0.1695 | 0.625 | 0.9167 | 0.5893 | 326.0s |
| skor_0.01 | 10/59 | 0.1695 | 0.625 | 0.9167 | 0.5893 | 322.6s |
| skor_0.02 | 10/59 | 0.1695 | 0.625 | 0.9167 | 0.5893 | 323.5s |
| skor_0.05 | 10/59 | 0.1695 | 0.625 | 0.9167 | 0.5893 | 324.7s |
| skor_0.1 | 10/59 | 0.1695 | 0.625 | 0.9167 | 0.5893 | 325.1s |
| wajib_bn_topk_3 | 10/59 | 0.1695 | 0.625 | 0.9167 | 0.5893 | 325.4s |
| wajib_bn_topk_5 | 10/59 | 0.1695 | 0.625 | 0.9167 | 0.5893 | 314.6s |

## Analisis

1. Hanya dua kelas efek: (a) tanpa konfirmasi, (b) dengan konfirmasi (semua
   parameter topk dan skor_min menghasilkan angka identik). Perbedaan hanya
   muncul antara wajib_bn (global) dan konfirmasi per-jendela (10 vs 12 FP).

2. Alasan: BirdNET pada data ini umumnya mendeteksi <= 1 spesies per jendela
   3 detik, sehingga topk_1 = topk_10 = skor_0.01 = skor_0.1. Konfirmasi
   per-jendela marginally lebih ketat dari wajib_bn global (2 berkas perbedaan).

3. TIDAK ADA konfigurasi yang memenuhi syarat recall target >= 0,70 sekaligus
   menurunkan FP. Konfirmasi BirdNET menekan FP (0.42 -> 0.17) tapi juga
   memotong recall (0.80 -> 0.63). Trade-off terlalu berat.

4. Konfigurasi TIDAK dipilih. cascade.yaml produksi TIDAK diubah.

## Perintah

```
python3 ml/sapu_konfirmasi.py
```

Berkas keluaran: `ml/reports/sapu_konfirmasi.json`, `ml/reports/sapu_konfirmasi.md`
