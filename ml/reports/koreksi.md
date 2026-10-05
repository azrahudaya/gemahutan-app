# Koreksi: klaim salah putaran sebelumnya

## Putaran 27 Sep 2026 (diaudit peninjau 27 Sep 21.30)

Angka diukur ulang oleh peninjau, bukan dari laporan otomatis.

| Klaim di commit/laporan | Kenyataan (diukur ulang) |
|---|---|
| A02 "ruff All checks passed" | 2 error di `ml/uji_independen.py` (F541 baris 80, B905 baris 174). Sekarang sudah diperbaiki. |
| A01 snapshot diperbaiki | Test dan fixture memakai jalur ReLU; mesin produksi (linear) berbeda sampai 0,0505 dari fixture. Test mengunci bug lama. Sekarang dibangun ulang lewat engine produksi (B02). |
| A06 "ambang per spesies di lipatan dalam, bootstrap berkelompok" | Tidak ada kode ambang; CI95 mem-bootstrap 5 angka rata-rata lipatan (termasuk nomor lipatan dan C), bukan grup perekam. Sekarang diperbaiki (B04). |
| E04 "acc 0,794 naik dari 0,756" | Jendela dipilih dengan `argmax(probs[:, target])` = memakai label. Tanpa label: model E04 0,7405, checkpoint produksi 0,7557. Model E04 LEBIH BURUK dari produksi. |
| Lampiran 1 "GAGAL/BLOCKED: tidak ada" | Empat butir di atas gagal. |

### Angka benar (uji independen 131 klip, tanpa label)

| Model | Acc (jendela terbaik, tanpa label) | Catatan |
|---|---|---|
| Checkpoint produksi (LR v3) | 0,7557 | Ini baseline yang benar |
| Model resep E04 (normalisasi lipatan) | 0,7405 | Lebih buruk dari produksi |

Kesimpulan: klaim "naik" di E04 salah karena dua angka dihitung dengan metode
berbeda (memakai label vs tanpa label). Angka tidak sebanding.

## Lampiran 6 (koreksi putaran open-set gerbang lisensi)

- Kesimpulan v5 pada putaran sebelumnya tidak berdasar. Tujuan v5 adalah menekan deteksi palsu, tetapi deteksi palsu v5 belum diukur saat itu.
- v5 mengubah dua faktor sekaligus: sumber negatif (iNat diganti XC) dan jumlah data negatif. Efeknya tidak terisolasi.
- Syarat gerbang lama "per spesies pada 127 klip uji" adalah keliru untuk keputusan, karena support terlalu kecil. Diganti G2 yang memakai F1 per spesies dari OOF CV.

Bukti putaran ini ada di `ml/reports/banding_v3_v5_v6.md` dan `ml/runs/l6/*/gerbang_g2.json`.

## Putaran Lampiran 3 (diaudit peninjau 28 Sep 2026 10.00)

Keenam butir dari Lampiran 4 bagian "Koreksi atas putaran Lampiran 3":

### 1. T3 tidak dikerjakan sesuai perintah (C17)

**Kesalahan**: Lisensi 3.205 klip iNaturalist tidak diambil dari API. Semua
klip iNat langsung dibuang dari dataset tanpa dasar bukti. Itu keputusan data
yang besar -- dataset menyusut dari 8.102 ke 4.897 klip latih -- tanpa satu pun
pemanggilan API iNaturalist.

**Yang seharusnya**: Ambil lisensi tiap observasi iNat dari
`https://api.inaturalist.org/v1/observations/{id}` (1 req/dtk, cache di
`ml/data/cache_api/`). Hanya klip yang benar-benar ND, all rights reserved,
atau tidak memiliki lisensi yang dikeluarkan.

### 2. v4 mengubah dua hal sekaligus (C18)

**Kesalahan**: Kandidat v4 mengubah (a) seleksi jendela latih DAN (b)
menghilangkan semua 3.205 klip iNat dalam satu langkah. Ketika uji independen
turun 0,7557 -> 0,7252, kesimpulannya "overfit jendela latih". Kesimpulan itu
tidak didukung data karena dua faktor berubah bersamaan.

**Yang seharusnya**: Isolasi faktor satu per satu. (a) v3 + filter lisensi
saja, (b) v3 + jendela energi saja, (c) v3 + jendela terpilih BirdNET saja.
Bandingkan dengan pool evaluasi yang sama persis.

### 3. Klaim "CV naik 0,729 -> 0,766" melanggar B1

**Kesalahan**: Pool CV berbeda antara v3 dan v4: 794 vs 894 Xeno-canto, 4.130
vs 7.335 non-XC. Angka tidak sebanding karena data evaluasi berbeda.

**Yang seharusnya**: Setiap perbandingan kandidat memakai pool evaluasi yang
sama persis (jumlah dan sha256 daftar id). Tanpa itu, klaim "naik"/"turun"
tidak sah.

### 4. Kebijakan T4 ditanam di cascade.py tanpa gerbang (D12)

**Kesalahan**: `margin_top1_top2: 0.3`, `min_kemunculan_ulang: 2`, dan
`ambang_kuat: 0.5` ditanam langsung di `ml/configs/cascade.yaml` DAN
hardcoded di `ml/engines/cascade.py` (konstanta `MIN_KEMUNCULAN_ULANG = 2`,
`AMBANG_KUAT = 0.5`). Rebuild image akan memasang kebijakan ini ke produksi
tanpa pernah lulus gerbang G.

**Yang seharusnya**: Konfigurasi cascade hanya berubah lewat gerbang. Sha256
`cascade.yaml` dicatat di `MANIFEST.json` sebagai `cascade_config_sha256`.
Kebijakan eksperimental disimpan di `ml/configs/kandidat/`.

### 5. Eksperimen wajib belum lengkap (C13, C14, C15)

**Kesalahan**: Skor energi (d) dan syarat kemunculan (e) belum dicoba.
Konfirmasi BirdNET hanya diuji hidup/mati tanpa sapuan ambang
(0,05/0,1/0,2/0,3). T6 (data spesies lemah dan negatif sulit) belum
dikerjakan.

**Yang seharusnya**: Semua eksperimen wajib di Lampiran 4 K3 harus
terdokumentasi di `ml/reports/hasil_negatif.md` sebelum status MELESET
diklaim. Tanpa itu, C13, C14, C15 dihitung GAGAL, bukan MELESET.

### 6. Berhenti tanpa laporan

**Kesalahan**: Pekerjaan berhenti tanpa `BERHENTI.md`, tanpa
`hasil_negatif.md`. `progres_L3.json` usang. Usulan hapus `ml/data/degraded`
salah -- ukurannya 279 MB, bukan 12 GB.

**Yang seharusnya**: Setiap penghentian menulis `BERHENTI.md` dengan keluaran
kedua audit dan sisa pekerjaan. Tidak boleh mengusulkan penghapusan data tanpa
mengukur ukurannya dulu.

## Putaran ML_10 (diaudit peninjau 2 Oktober 2026)

### 1. Judul commit a71a5a9 "LULUS C14" berlebihan

**Kesalahan**: judul commit `a71a5a9` menulis "K3 jendela bersuara: F1 CV 0,8051
LULUS C14". C14 punya TIGA syarat, dan yang diukur saat itu hanya dua:

| Syarat C14 | Batas | K3 | Hasil |
|---|---:|---:|---|
| F1 CV | >= 0,78 | 0,8051 | lulus |
| CI95 bawah F1 CV | >= 0,75 | 0,7649 | lulus |
| F1 uji independen | >= 0,75 | 0,5953 | GAGAL |

Angka F1 independen K3 0,5953 ada di `ml/reports/k3_bersuara/uji_independen.json`
dan bahkan LEBIH RENDAH dari produksi 0,6069
(`ml/reports/uji_independen.json`). Jadi bukan cuma "belum diukur": syaratnya
memang tidak terpenuhi, dengan selisih 0,1547 dari batas.

`ops/audit_model.py` baris 359 memeriksa ketiganya sekaligus
(`cv["f1"] >= 0.78 and cv["lo"] >= 0.75 and ind["f1"] >= 0.75`), jadi audit akan
tetap menandai C14 MELESET untuk K3. Status C14 yang benar untuk K3: BELUM LULUS.

**Yang seharusnya**: nama syarat kelulusan hanya dipakai setelah SEMUA bagiannya
terukur dan terpenuhi. Kalau sebagian lulus, tulis bagian mana beserta angkanya,
jangan nama syaratnya.

### 2. Kolom "C14 LULUS" untuk Perch di k6_perch/README.md juga berlebihan

Tabel `ml/reports/k6_perch/README.md` memberi Perch kolom "C14: LULUS" atas dasar
F1 CV 0,8386 dan CI bawah 0,7960. Pada saat itu README yang sama sudah mencatat
bahwa F1 independen Perch TIDAK BISA dihitung (0 dari 135 klip uji independen
punya embedding Perch), jadi syarat ketiga C14 tidak diketahui, bukan lulus.
Kolomnya diganti menjadi status per syarat.

**Yang berlaku sekarang**: sepanjang ML_10 BELUM ADA satu pun komponen yang lulus
C14 penuh. Yang terbukti: dua komponen (K3 BirdNET jendela bersuara, K6 Perch)
melewati bagian F1 CV dan CI bawah pada pool yang sha256-nya identik.

## Prinsip yang dilanggar (berlaku untuk kedua putaran)

1. Pemilihan jendela/sampel tidak boleh memakai label (data leakage).
2. Angka "naik"/"lebih baik" hanya boleh dibandingkan antar metode yang sama
   pada data yang sama (B1).
3. Laporan status harus mencerminkan hasil audit, bukan klaim sendiri.
4. Perilaku produksi hanya berubah lewat gerbang, bukan lewat edit langsung.
5. Satu eksperimen, satu perubahan. Pool evaluasi sama persis.
6. Keputusan data hanya berdasarkan bukti (misalnya lisensi dari API), bukan
   asumsi.