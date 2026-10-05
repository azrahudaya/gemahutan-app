# Analisis Galat Spektrogram (Uji Bersih)

Dipilih 4 kelas dengan support kecil (rentan karena data kurang) 
dan 4 confusion pair dari `ml/reports/confusion_top.md`. 
Untuk tiap klip ditampilkan spektrogram log-mel 128-bin dan 
distribusi energi. Label benar diambil dari manifest.

| # | clip | label benar | tebakan | confidence | jenis | species di folder |
|---|---|---|---|---|---|---|

## Hipotesis penyebab

1. **Support kecil** (Prinia familiaris n=1, Gallus gallus n=1). Satu klip uji artinya recall otomatis 0 atau 100. Tanpa data latih yang cukup, jaringan tidak punya pola spektral yang stabil untuk spesies ini.
2. **Confusion antar passerine bersuara tipis** (Aegithina tiphia vs Cinnyris jugularis, Hirundo tahitica vs Cinnyris jugularis). Burung kecil dengan kicauan nyaring di pita 4 sampai 8 kHz punya pola spektral mirip, dan embedding BirdNET sudah mengkodekan timbre global sehingga bedanya tipis.
3. **Suara vokal rendah mirip panggilan kawin** (Amaurornis phoenicurus vs Merops philippinus). Kedua spesies punya panggilan berulang di bawah 2 kHz; pada jendela 3 detik kadang hanya satu panggilan yang aktif sehingga keyakinan meloncat ke kelas lain.
4. **Kelas ambigu di kelas _negative** (Arachnothera longirostra vs Dicrurus macrocercus, Aplonis panayensis vs Gallus gallus). Kelas negatif berisi Xeno-canto non-target, tapi kadang ada suara ambient yang mirip kicauan, jadi model ragu.

Gambar: `docs/proposal/figures/fig11_error_analysis.png`.