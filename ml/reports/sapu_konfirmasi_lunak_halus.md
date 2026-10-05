# Sapuan konfirmasi lunak (S1)

Konfigurasi baru: `trackb_konfirmasi_skor_min_lunak`
Kalau Track B confidence >= threshold ini, skip konfirmasi BirdNET.
Metrik dihitung HANYA dari bagian pilih.

| Konfigurasi | FP pilih | FP rate | Recall target | Phone P | Phone R | Waktu |
|---|---:|---:|---:|---:|---:|---:|
| tanpa_konfirmasi | 25/59 | 0.4237 | 0.7981 | 0.8298 | 0.6964 | 304.8s |
| wajib_bn_keras | 12/59 | 0.2034 | 0.6442 | 0.9189 | 0.6071 | 299.1s |
| lunak_0.91 | 13/59 | 0.2203 | 0.75 | 0.9024 | 0.6607 | 294.6s |
| lunak_0.92 | 13/59 | 0.2203 | 0.75 | 0.9024 | 0.6607 | 304.2s |
| lunak_0.93 | 13/59 | 0.2203 | 0.75 | 0.9024 | 0.6607 | 296.1s |
| lunak_0.94 | 13/59 | 0.2203 | 0.7404 | 0.9024 | 0.6607 | 304.6s |
