# Data Tambahan: Pengecualian dan Aturan Unduh Negatif XC

Dokumen ini mencatat semua pengecualian untuk unduhan contoh negatif
Xeno-canto (`ml/unduh_negatif_xc.py`), sesuai aturan peninjau 28 Sep 2026.

## Tujuan

Mengganti 3.205 klip iNaturalist (2.647 burung + 558 serangga/mamalia) yang
lisensinya tidak bisa dibuktikan per klip, dengan klip Xeno-canto yang
lisensinya jelas dan non-ND. Sekaligus menyediakan data negatif untuk
menekan deteksi palsu (butir 6).

## Aturan unduh

- Spesies: burung Indonesia + Malaysia, Singapura, Brunei, Filipina, Thailand.
- BUKAN 25 spesies target.
- Kualitas A/B/C, lisensi tanpa ND (CC BY, CC BY-SA, CC BY-NC, CC BY-NC-SA).
- Maks 8 klip/spesies, maks 3 klip/perekam/spesies.
- Target >=300 spesies, total maks 3000 klip (pengganti 2.647 klip iNat burung).
- Belalang/jangkrik dan kelelawar untuk pengganti 558 klip serangga/mamalia,
  maks 600 klip.
- API maks 1 permintaan/detik, di-cache di `ml/data/cache_api/`.
- Berhenti kalau disk < 6 GB.

## Pengecualian (DILARANG diunduh)

### 1. Semua spesies di field/other (29 spesies dari pembagian_openset.json)

Bagian "pilih" (14): Accipiter badius, Acridotheres javanicus,
Aethopyga mystacalis, Alcedo meninting, Centropus sinensis, Collocalia linchi,
Dendrocygna arcuata, Dicaeum trochileum, Hemipus hirundinaceus, Ketupa ketupu,
Merops viridis, Orthotomus ruficeps, Streptopelia bitorquata, Turnix suscitator.

Bagian "lapor" (15): Aethopyga siparaja, Corvus enca, Halcyon cyanoventris,
Lonchura leucogastroides, Lonchura maja, Megalaima armillaris,
Megalaima javensis, Merops leschenaulti, Nectarinia jugularis,
Nisaetus bartelsi, Oriolus chinensis, Pellorneum rostratum,
Pericrocotus cinnamomeus, Treron griseicauda, Zosterops palpebrosus.

Alasan: kalau spesies bagian "pilih" ikut dilatih, sapuan di bagian "pilih"
jadi terlalu optimistis (bocor dari data uji ke data latih).

### 2. Perekam di data evaluasi mana pun (351 perekam)

Semua perekam yang muncul di field/*, uji_independen, split uji lama, dan
pool CV. Sumber: `field/manifest.csv`, `uji_independen/manifest.csv`,
`manifest_v2.csv`, `xc_meta.json` (recordings + groups).

Alasan: perekam yang sama bisa punya karakter mic/lokasi mirip sehingga
membuat model "mengenal perekam" bukan spesies.

### 3. ID XC yang sudah ada di korpus (1.076 ID)

Semua `xc-*` di manifest_v2.csv, field/manifest.csv, uji_independen/manifest.csv,
dan xc_meta.json.

Alasan: hindari duplikat.

## Selisih spesies pengecoh (diminta peninjau)

`pembagian_openset.json` mencantumkan 14 + 15 = 29 spesies pengecoh.
`field/manifest.csv` kelompok other punya 22 spesies. Dari 29 spesies
pembagian, 21 ada di field/other dan 8 tidak ada. Tambahan 1 spesies di
field/other adalah Arachnothera longirostra, yang justru masuk 25 spesies
target (perlu dicatat sebagai anomali, tidak diubah).

Rincian 8 spesies pembagian yang tidak punya klip di field/other:

- Pilih (2): Acridotheres javanicus, Streptopelia bitorquata.
- Lapor (6): Halcyon cyanoventris, Megalaima armillaris, Megalaima javensis,
  Nectarinia jugularis, Oriolus chinensis, Zosterops palpebrosus.

Jadi 12 pilih + 9 lapor = 21 dari 29 spesies pembagian muncul di field/other.
`pembagian_openset.json` TIDAK diubah (file beku).

## Keluaran

- `ml/data/negatif_xc/` (audio)
- `ml/data/manifest_negatif_xc.csv` (manifest)
- Statistik akhir (jumlah spesies, klip, ukuran) ditulis setelah unduhan selesai.

## Status

Sedang berjalan. Disk awal 11 GB. Berhenti otomatis kalau < 6 GB.