# Uji asap rekaman YouTube, 3 Oktober 2026

**Ini uji asap, bukan evaluasi akurasi.** Tujuannya memastikan pipeline jalan pada audio lapangan
sungguhan (bukan klip Xeno-canto yang bersih). Label spesies di video tidak terverifikasi, jadi
angka di bawah TIDAK boleh dilaporkan sebagai akurasi lapangan. Audio hanya diunduh untuk uji lokal,
tidak disimpan di repo atau server publik, dan hak ciptanya tetap milik pengunggah.

Potongan menit 05:00 sampai 10:00 dari tiap video, diproses lewat akun tamu di stack lokal
(engine cascade, model produksi saat itu).

| Video | Durasi | Waktu proses | Deteksi |
|---|---|---|---|
| Java Island Rainforest (Earthfm, JM1nMP7NTZQ) | 5 menit | 12 dtk | Delimukan Zamrud 3x (maks 0,29), *Brachypteryx leucophris* 5x (maks 0,26) |
| Morning in Bali (Ladrhyn Bexx, zNAB8CG1b0M) | 5 menit | 12 dtk | Cekakak Sungai 1x (0,74) |
| Bali rice fields (Walkscapes, QdHoDc-ZHOo) | 5 menit | 12 dtk | Perkutut Jawa 2x (maks 0,39), Kareo Padi 3x (maks 0,33), Cekakak Sungai 2x (maks 0,27) |

Catatan:
- Pipeline selesai tanpa galat di ketiga klip, sekitar 25 kali lebih cepat dari waktu nyata di laptop tanpa GPU.
- Hanya satu deteksi di atas 0,5, jadi di halaman depan hanya Cekakak Sungai yang tampil sebagai "terdeteksi".
  Sisanya masuk "Kemungkinan lain". Ini sejalan dengan batasan yang sudah tercatat: skor turun pada audio lapangan.
- Spesies yang muncul masuk akal untuk habitatnya (sawah: Perkutut Jawa, Kareo Padi; pesisir Bali: Cekakak Sungai),
  tetapi belum dicek telinga ahli.
- Angka lapangan resmi tetap butuh rekaman sendiri yang diverifikasi (P1 di NEEDS_FROM_YOU.md).
