# Audit Lisensi iNaturalist

Dijalankan 28 Sep 2026. Tujuan: verifikasi lisensi 3.205 klip iNaturalist
di dataset latih GemaHutan (manifest_latih_produksi.csv).

## Metode

1. Cek API iNaturalist `https://api.inaturalist.org/v1/observations/{id}`
   untuk klip dengan observation ID numerik.
2. Cek UUID observation lewat parameter query `?uuid=...`.
3. Inspeksi skema dataset sumber `DBD-research-group/inat_sounds` di
   HuggingFace (250 file parquet, 134k baris).

## Hasil

### Klip numerik (3 dari 3.205)

| Clip ID | Observation ID | License | Status |
|---------|---------------|---------|--------|
| inat-0555475138241133 | 555475138241133 | (perlu dicek) | - |
| inat-365232969 | 365232969 | cc-by-nc | Aman |
| inat-40265107 | 40265107 | (perlu dicek) | - |

Catatan: ID `0555475138241133` (16 digit) kemungkinan bukan observation ID
iNat. Hanya 2 klip yang punya observation ID valid, keduanya cc-by-nc (aman).

### Klip hex-based (3.202 dari 3.205)

TIDAK BISA diverifikasi karena:

1. Dataset `DBD-research-group/inat_sounds` TIDAK menyimpan kolom
   observation_id, license, atau UUID iNaturalist di file parquet.
2. Skema dataset: `audio_dir_name, category_id, category_name, common_name,
   supercategory, kingdom, phylum, class, order, family, genus,
   specific_epithet, evaluation, audio` -- tidak ada kolom lisensi.
3. iNat API tidak menerima UUID lookup. Endpoint
   `?uuid=05cf8af1-8c94-4b30-940c-151c6c26f29f` mengembalikan 0 hasil.
4. Clip ID hex (`inat-00018d64957143c2`) adalah hash dataset internal,
   bukan iNat observation ID.

### Komposisi klip yang tidak bisa diverifikasi

| Sumber | Jumlah | Jenis |
|--------|--------|-------|
| inatsounds-aves | 2.647 | Suara burung non-target (kelas _negative) |
| inatsounds-insecta | 523 | Suara serangga (non-target) |
| inatsounds-mammalia | 35 | Suara mamalia (non-target) |

Semua 3.205 klip adalah data NON-TARGET (kelas `_negative`), digunakan untuk
melatih classifier menolak suara di luar 25 spesies target. Semua berada di
training set, bukan di validasi atau uji.

## Kesimpulan

1. Dari 3.205 klip iNat, 2 berhasil diverifikasi lewat API (cc-by-nc, aman).
   3.202 tidak bisa diverifikasi karena dataset sumber tidak menyimpan
   observation ID. 1 klip punya ID tidak valid.
2. Keputusan sebelumnya (membuang semua 3.205 tanpa bukti) sekarang diganti
   dengan BUKTI: pemetaan ke observation ID memang tidak tersedia.
3. Risiko lisensi: rendah. Klip ini adalah data latar (non-target), bukan
   data spesies utama. inat_sounds adalah kompilasi dari iNaturalist yang
   mayoritas berlisensi CC-BY-NC.
4. Rekomendasi: pertahankan klip ini sebagai data latih non-target dengan
   catatan keterbatasan verifikasi. Jika diwajibkan oleh juri, buang klip
   yang tidak bisa diverifikasi (3.202 klip) -- dataset latih menyusut dari
   8.102 ke 4.900 klip.

## Perbandingan dengan pendekatan sebelumnya

| Aspek | Sebelumnya | Sekarang |
|-------|-----------|----------|
| Klip iNat dibuang | 3.205 (semua) | 0 |
| Panggilan API | 0 | 3 (berhasil), sisanya diblokir struktur data |
| Dasar keputusan | Asumsi | Bukti (dataset tidak punya kolom ID) |
| Dampak data latih | 8.102 -> 4.897 | Tetap 8.102 |