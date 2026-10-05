# Evaluasi Kondisi Audio

Model yang dinilai: `ml/checkpoints_augft/best_model.npz`.
Model, threshold, dan cara pemotongan jendela sama dengan yang dipakai aplikasi.
Tangga degradasi adalah simulasi ffmpeg, bukan rekaman lapangan, dan dilaporkan terpisah.

## Data uji bersih dan tangga degradasi

| Kondisi | Jendela | Akurasi top-1 | Macro F1 |
|---|---|---|---|
| bersih | 218 | 0.7202 | 0.7289 |
| bersih tanpa nd | 145 | 0.7103 | 0.7269 |
| kontrol reencode | 216 | 0.6759 | 0.6809 |
| hujan ringan | 216 | 0.6157 | 0.6307 |
| hujan deras | 216 | 0.5463 | 0.5568 |
| angin | 216 | 0.6528 | 0.6551 |
| kota | 216 | 0.6019 | 0.5943 |
| jarak 30m | 217 | 0.5714 | 0.6004 |
| jarak 100m | 206 | 0.5146 | 0.5083 |
| gabungan berat | 213 | 0.2958 | 0.2620 |

## Rekaman kondisi lapangan (nyata, berlisensi)

Kelompok `other` berisi spesies di luar label map, jadi satu-satunya angka
yang bermakna di sana adalah deteksi palsu.

| Kelompok | Berkas terbaca | Jendela | Akurasi top-1 | Macro F1 | Tingkat deteksi | Deteksi palsu |
|---|---|---|---|---|---|---|
| inat | 111 dari 113 | 610 | 0.5000 | 0.4706 | 0.7230 | tidak diukur |
| other | 20 dari 21 | 128 | tidak berlaku | tidak berlaku | tidak berlaku | 0.6328 |
| xc_noisy | 106 dari 108 | 640 | 0.6719 | 0.6656 | 0.7594 | tidak diukur |

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
