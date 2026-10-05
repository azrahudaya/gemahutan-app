# Evaluasi Kondisi Audio

Model yang dinilai: `ml/checkpoints/best_model.npz`.
Model, threshold, dan cara pemotongan jendela sama dengan yang dipakai aplikasi.
Tangga degradasi adalah simulasi ffmpeg, bukan rekaman lapangan, dan dilaporkan terpisah.

## Data uji bersih dan tangga degradasi

| Kondisi | Jendela | Akurasi top-1 | Macro F1 |
|---|---|---|---|
| bersih | 127 | 0.5512 | 0.5315 |
| bersih tanpa nd | 127 | 0.5512 | 0.5315 |
| kontrol reencode | 95 | 0.5684 | 0.5185 |
| hujan ringan | 95 | 0.4947 | 0.4682 |
| jarak 30m | 94 | 0.4681 | 0.4564 |

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
