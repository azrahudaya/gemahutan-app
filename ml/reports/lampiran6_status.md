# Lampiran 6: Status Kerja ML_08

Dibuat: 1 Oktober 2026

## Butir L6

### L6-3: Konfirmasi BirdNET bertingkat
- **Status**: BELUM SELESAI
- **Keterangan**: Belum diimplementasi. Perlu menambahkan konfigurasi konfirmasi bertingkat (top-k dan skor minimum) di cascade.yaml.
- **Skrip**: `ml/engines/cascade.py` perlu update untuk mendukung konfirmasi bertingkat.

### L6-4: Jendela bersuara
- **Status**: BELUM SELESAI
- **Keterangan**: Perlu membuat skrip untuk mengekstraksi jendela bersuara dari rekaman.

### L6-5: Lisensi iNat
- **Status**: BELUM SELESAI
- **Keterangan**: Klaim SELESAI keliru.grep tidak cukup untuk verifikasi lisensi.
  - Klip iNat berjumlah **3205**, bukan 272 atau 924.
  - Perlu mengunduh anotasi resmi iNatSounds 2024 dari `github.com/visipedia/inat_sounds`.
  - Setiap klip di `manifest_latih_produksi.csv` harus dicocokkan ke anotasi resmi.
  - Kolom `license`, `license_url`, dan `sumber_lisensi` harus diisi.
  - Klip berlisensi ND atau yang tidak ketemu di anotasi harus DIKELUARKAN dari kandidat baru.

### L6-6: Korpus v7 (augmentasi)
- **Status**: DILEWATI (B5)
- **Keterangan**: Augmentasi dengan jendela bersuara dan latar lapangan. Dilewati karena B5 (jendela bersuara + augmentasi) lebih komprehensif.

## Catatan

- L6-3, L6-4, dan L6-5 harus selesai sebelum korpus v7 dapat dibuat.
- Status SELESAI hanya boleh ditulis bila berkas keluaran ada dan angka perintah yang benar-benar dijalankan.
