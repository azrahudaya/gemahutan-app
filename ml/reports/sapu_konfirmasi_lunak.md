# Sapuan konfirmasi lunak (S1)

Konfigurasi baru: `trackb_konfirmasi_skor_min_lunak`
Kalau Track B confidence >= threshold ini, skip konfirmasi BirdNET.
Metrik dihitung HANYA dari bagian pilih.

| Konfigurasi | FP pilih | FP rate | Recall target | Phone P | Phone R | Waktu |
|---|---:|---:|---:|---:|---:|---:|
| tanpa_konfirmasi | 25/59 | 0.4237 | 0.7981 | 0.8298 | 0.6964 | 266.0s |
| wajib_bn_keras | 12/59 | 0.2034 | 0.6442 | 0.9189 | 0.6071 | 260.6s |
| lunak_0.5 | 22/59 | 0.3729 | 0.7885 | 0.8667 | 0.6964 | 286.7s |
| lunak_0.6 | 19/59 | 0.322 | 0.7788 | 0.8636 | 0.6786 | 272.6s |
| lunak_0.7 | 16/59 | 0.2712 | 0.7788 | 0.8636 | 0.6786 | 282.4s |
| lunak_0.8 | 16/59 | 0.2712 | 0.7692 | 0.9048 | 0.6786 | 265.4s |
| lunak_0.9 | 13/59 | 0.2203 | 0.75 | 0.9024 | 0.6607 | 277.9s |
| lunak_0.95 | 13/59 | 0.2203 | 0.7404 | 0.9024 | 0.6607 | 272.5s |
| lunak_0.99 | 12/59 | 0.2034 | 0.6731 | 0.9231 | 0.6429 | 269.9s |
