# Evaluasi Kondisi Audio

Model yang dinilai: `ml/checkpoints/best_model.npz`.
Model, threshold, dan cara pemotongan jendela sama dengan yang dipakai aplikasi.
Tangga degradasi adalah simulasi ffmpeg, bukan rekaman lapangan, dan dilaporkan terpisah.

## Data uji bersih dan tangga degradasi

| Kondisi | Jendela | Akurasi top-1 | Macro F1 |
|---|---|---|---|
| bersih | 127 | 0.6850 | 0.6630 |
| bersih tanpa nd | 127 | 0.6535 | 0.6200 |
| kontrol reencode | 126 | 0.6032 | 0.5810 |
| hujan ringan | 126 | 0.5635 | 0.5564 |
| hujan deras | 125 | 0.4560 | 0.4736 |
| angin | 126 | 0.5238 | 0.5207 |
| kota | 125 | 0.5120 | 0.5005 |
| jarak 30m | 124 | 0.4758 | 0.5057 |
| jarak 100m | 115 | 0.5304 | 0.5009 |
| gabungan berat | 123 | 0.1626 | 0.1881 |

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
