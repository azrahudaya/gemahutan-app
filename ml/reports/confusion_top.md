# Confusion Teratas (Uji Bersih, Normalized per Baris)

Sepuluh pasangan kelas yang paling sering keliru diprediksi, 
diurutkan dari nilai normalized-row terbesar. 
`cm_norm` adalah proporsi jendela kelas-benarnya yang diprediksi 
sebagai kelas-target. `count` adalah jumlah jendela.

| # | cm_norm | count | Label benar | Diprediksi sebagai |
|---|---------|-------|-------------|---------------------|
| 1 | 1.000 | 1 | Prinia familiaris | Passer montanus |
| 2 | 1.000 | 1 | Gallus gallus | Aplonis panayensis |
| 3 | 0.667 | 2 | Dicrurus macrocercus | Cinnyris jugularis |
| 4 | 0.500 | 2 | Lonchura punctulata | _negative |
| 5 | 0.333 | 1 | Hirundo tahitica | Haliastur indus |
| 6 | 0.333 | 1 | Hirundo tahitica | Cinnyris jugularis |
| 7 | 0.333 | 1 | Dicrurus macrocercus | Orthotomus sutorius |
| 8 | 0.250 | 1 | Rhipidura javanica | Aegithina tiphia |
| 9 | 0.250 | 1 | Haliastur indus | Lonchura punctulata |
| 10 | 0.250 | 1 | Haliastur indus | Hirundo tahitica |

Total jendela uji: 127. Akurasi top-1: 0.6299.