# Evaluasi Kondisi Audio

Model yang dinilai: `ml/checkpoints_aug/best_model.npz`.
Model, threshold, dan cara pemotongan jendela sama dengan yang dipakai aplikasi.
Tangga degradasi adalah simulasi ffmpeg, bukan rekaman lapangan, dan dilaporkan terpisah.

## Data uji bersih dan tangga degradasi

| Kondisi | Jendela | Akurasi top-1 | Macro F1 |
|---|---|---|---|
| bersih | 218 | 0.6009 | 0.6093 |
| bersih tanpa nd | 145 | 0.5862 | 0.6095 |
| kontrol reencode | 216 | 0.5926 | 0.6005 |
| hujan ringan | 216 | 0.5278 | 0.5433 |
| hujan deras | 216 | 0.4907 | 0.5246 |
| angin | 216 | 0.5602 | 0.5649 |
| kota | 216 | 0.5556 | 0.5538 |
| jarak 30m | 217 | 0.5069 | 0.5323 |
| jarak 100m | 206 | 0.4806 | 0.4761 |
| gabungan berat | 213 | 0.2958 | 0.2946 |

## Rekaman kondisi lapangan (nyata, berlisensi)

Kelompok `other` berisi spesies di luar label map, jadi satu-satunya angka
yang bermakna di sana adalah deteksi palsu.

| Kelompok | Berkas terbaca | Jendela | Akurasi top-1 | Macro F1 | Tingkat deteksi | Deteksi palsu |
|---|---|---|---|---|---|---|
| inat | 111 dari 113 | 610 | 0.4131 | 0.3912 | 0.6672 | tidak diukur |
| other | 20 dari 21 | 128 | tidak berlaku | tidak berlaku | tidak berlaku | 0.6172 |
| xc_noisy | 106 dari 108 | 640 | 0.5750 | 0.5932 | 0.7359 | tidak diukur |

Catatan pembacaan:

- Angka bersih adalah baseline yang sudah dilaporkan di eval.md.
- Baris bersih tanpa ND mengulang baseline hanya pada klip uji yang lisensinya
  mengizinkan karya turunan, karena pipeline ini memotong klip dan melatih model.
- Klip ND di manifest: 446 dari 1370, 73 di antaranya masuk split uji.
- Klip lapangan berlisensi ND yang disisihkan: 0.
- Kolom berkas terbaca penting: berkas yang tidak bisa didekode dihitung, bukan dianggap benar.
- 50 klip lapangan ND sudah dibuang dari korpus sebelum evaluasi ini, karena pipeline memotong klip jadi karya turunan.
- Kelompok pengecoh berisi spesies yang tidak dikenal classifier, jadi setiap
  deteksi ke kelas target di kelompok itu dihitung sebagai deteksi palsu.
- Simulasi degradasi mengukur ketahanan terhadap gangguan, bukan pengganti uji lapangan.
