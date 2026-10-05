# gemahutan-embeddings-v2

Embedding BirdNET untuk korpus latih GemaHutan versi 2, siap dipakai melatih classifier tanpa mengunduh audio.

## Isi

| Berkas | Isi |
|---|---|
| `embeddings_v2/embeddings.npy` | matriks 8258 x 1024 float32 |
| `embeddings_v2/labels.npy` | label integer 8258 baris |
| `embeddings_v2/clip_ids.json` | urutan clip_id, sejajar baris embeddings |
| `embeddings_v2/label_map.json` | peta nama kelas ke indeks, 26 kelas |
| `manifest_v2.csv` | daftar klip dengan sumber, lisensi, hash |
| `splits_v2.json` | pembagian latih, validasi, uji |
| `checkpoints_v2/normalization.npz` | mean dan std 1024 dimensi, dihitung dari train saja |

## Cara menghasilkan

Audio diunduh dari empat repo data GemaHutan, lalu embedding diambil dari lapisan GLOBAL_AVG_POOL BirdNET 2.4, tensor ke-545, dengan jendela 3 detik pada 48 kHz.

Perintah:

```bash
python3 ml/data/extract_embeddings.py \
  --manifest ml/data/manifest_v2.csv \
  --out-dir ml/embeddings_v2 \
  --ckpt-dir ml/checkpoints_v2
```

## Komposisi korpus

| Split | Baris |
|---|---|
| train | 8004 |
| val | 127 |
| test | 127 |

| Sumber | Klip |
|---|---|
| Xeno-canto lama | 923 |
| SEA-Bird ND-free | 3124 |
| iNatSounds | 3205 |
| ULM ND-free | 1006 |

## Yang harus diperhatikan sebelum memakai

- Split lama dipertahankan apa adanya supaya angka uji bisa dibandingkan dengan baseline 0,6772. Semua data eksternal masuk train, tidak ada yang masuk validasi atau uji.
- Kebocoran sudah diperiksa: tidak ada ID rekaman atau hash berkas yang muncul di lebih dari satu split. Pemeriksaannya ada di `ops/verifikasi_split_v2.py`.
- Enam spesies punya 271 sampai 393 klip. Angka itu datang dari 78 sampai 118 rekaman, karena klip SEA-Bird adalah potongan 3 detik dari satu rekaman. Keragamannya nyata tetapi sekitar 2 sampai 2,5 kali lipat, bukan 10 kali.
- Kelas `_negative` berisi 5650 klip, jauh lebih besar dari kelas mana pun. Bobot kelas harus dipakai saat melatih.
- Kelas `_negative` memuat burung non-target dari Eropa dan Amerika, serangga, dan mamalia. Yang non-target itu memang harus diprediksi `_negative`.
- Normalisasi disimpan terpisah di `checkpoints_v2/normalization.npz`. Jangan menimpanya ke `ml/checkpoints/normalization.npz` milik model produksi.

## Repo ini privat

Audio sumbernya berlisensi CC BY-NC-SA dan CC BY-NC, artinya pemakaian komersial tidak diizinkan.
