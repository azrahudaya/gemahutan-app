# Evaluasi Kondisi Audio

Model yang dinilai: `ml/checkpoints_v2/best_model.npz`.
Model, threshold, dan cara pemotongan jendela sama dengan yang dipakai aplikasi.
Tangga degradasi adalah simulasi ffmpeg, bukan rekaman lapangan, dan dilaporkan terpisah.

## Data uji bersih dan tangga degradasi

| Kondisi | Jendela | Akurasi top-1 | Macro F1 |
|---|---|---|---|
| bersih | 127 | 0.7323 | 0.6755 |
| bersih tanpa nd | 127 | 0.7402 | 0.6813 |

## Rekaman kondisi lapangan (nyata, berlisensi)

Kelompok `other` berisi spesies di luar label map, jadi satu-satunya angka
yang bermakna di sana adalah deteksi palsu.

| Kelompok | Berkas terbaca | Jendela | Akurasi top-1 | Macro F1 | Tingkat deteksi | Deteksi palsu |
|---|---|---|---|---|---|---|
| inat | 111 dari 113 | 610 | 0.4607 | 0.4972 | 0.7607 | tidak diukur |
| other | 20 dari 21 | 128 | tidak berlaku | tidak berlaku | tidak berlaku | 0.5625 |
| xc_noisy | 106 dari 108 | 640 | 0.6687 | 0.7151 | 0.8219 | tidak diukur |

Catatan pembacaan:

- Angka bersih adalah baseline yang sudah dilaporkan di eval.md.
- Baris bersih tanpa ND mengulang baseline hanya pada klip uji yang lisensinya
  mengizinkan karya turunan, karena pipeline ini memotong klip dan melatih model.
- Klip ND di manifest: 0 dari 1370, 0 di antaranya masuk split uji.
- Klip lapangan berlisensi ND yang disisihkan: 0.
- Kolom berkas terbaca penting: berkas yang tidak bisa didekode dihitung, bukan dianggap benar.
- 50 klip lapangan ND sudah dibuang dari korpus sebelum evaluasi ini, karena pipeline memotong klip jadi karya turunan.
- Kelompok pengecoh berisi spesies yang tidak dikenal classifier, jadi setiap
  deteksi ke kelas target di kelompok itu dihitung sebagai deteksi palsu.
- Simulasi degradasi mengukur ketahanan terhadap gangguan, bukan pengganti uji lapangan.
