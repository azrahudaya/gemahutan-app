# Eksperimen Kondisi Lapangan

Tiga model dinilai pada data uji, tangga degradasi simulasi, dan korpus lapangan
nyata yang sama. Threshold keputusan dan cara pemotongan jendela identik.

1. produksi, `ml/checkpoints/best_model.npz`, dilatih hanya pada audio bersih.
2. augmentasi dari nol, `ml/checkpoints_aug/best_model.npz`, 655 klip bersih plus
   1951 klip simulasi hujan deras, kota, dan jarak 30 meter, dilatih dari awal.
3. augmentasi fine-tune, `ml/checkpoints_augft/best_model.npz`, data yang sama
   tetapi dimulai dari bobot model produksi, 80 epoch, lr 0,0005, normalisasi
   tetap memakai statistik model produksi.

## Akurasi top-1 per kondisi

| Kondisi | Jendela | produksi | augmentasi dari nol | augmentasi fine-tune |
|---|---|---|---|---|
| bersih | 218 | 0.7156 | 0.6009 | 0.7202 |
| bersih tanpa nd | 145 | 0.7034 | 0.5862 | 0.7103 |
| kontrol reencode | 216 | 0.6759 | 0.5926 | 0.6759 |
| hujan ringan | 216 | 0.6065 | 0.5278 | 0.6157 |
| hujan deras | 216 | 0.5370 | 0.4907 | 0.5463 |
| angin | 216 | 0.6250 | 0.5602 | 0.6528 |
| kota | 216 | 0.5880 | 0.5556 | 0.6019 |
| jarak 30m | 217 | 0.5622 | 0.5069 | 0.5714 |
| jarak 100m | 206 | 0.5194 | 0.4806 | 0.5146 |
| gabungan berat | 213 | 0.2817 | 0.2958 | 0.2958 |

## Korpus lapangan nyata

| Kelompok | Berkas terbaca | Jendela | produksi | augmentasi dari nol | augmentasi fine-tune |
|---|---|---|---|---|---|
| xc_noisy | 106 dari 108 | 640 | 0.6594 | 0.5750 | 0.6719 |
| inat | 111 dari 113 | 610 | 0.5082 | 0.4131 | 0.5000 |
| other (pengecoh) | 20 dari 21 | 128 | deteksi palsu 0.6172 | tidak diukur | deteksi palsu 0.6328 |

## Kesimpulan

- Melatih ulang dari nol dengan data simulasi merugikan: akurasi bersih turun dari
  0,7156 ke 0,6009 dan seluruh tingkat degradasi ikut turun kecuali gabungan berat.
  Penyebabnya overfit, train accuracy 0,863 sementara validasi 0,58, dan validasi
  memuncak di sekitar epoch 100 lalu menurun. Sweep 60, 120, dan 180 epoch tidak
  memperbaiki val_acc di atas 0,5806.
- Fine-tune dari bobot produksi tidak merusak apa pun dan menaikkan hampir semua
  angka simulasi, termasuk rekaman kotor Xeno-canto yang nyata (0,6594 ke 0,6719).
  Tetapi selisihnya kecil, berkisar 0,5 sampai 2,8 poin, dan tidak muncul pada
  rekaman ponsel iNaturalist (0,5082 ke 0,5000) yang justru paling mirip lapangan.
  Deteksi palsu pada kelompok pengecoh juga sedikit naik, 0,6172 ke 0,6328.
- Karena itu kesimpulan jujurnya: augmentasi simulasi belum terbukti menaikkan
  performa lapangan. Yang dibutuhkan rekaman lapangan asli, bukan simulasi yang
  ditambah. Model yang dipakai aplikasi tetap model produksi.
