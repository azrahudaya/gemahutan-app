# Protokol Rekam Lapangan GemaHutan

Tujuan: mengumpulkan minimal 30 menit rekaman sendiri dari lokasi target,
diverifikasi ahli lewat aplikasi, untuk dievaluasi end-to-end (butir 10 rubrik).

## Lokasi

- Pilih 1 sampai 3 lokasi yang sama dengan kawasan konservasi target
  (Universitas Gunadarma dan sekitarnya).
- Catat koordinat (lat/lon) saat mulai rekam. Audio tidak membawa koordinat,
  lokasi dari `sites.geom` saat unggah.

## Jam

- Subuh: 05.00 sampai 07.00 WIB (puncak aktivitas burung).
- Sore: 16.00 sampai 18.00 WIB.
- Minimal 2 sesi (subuh + sore) per lokasi.

## Durasi per sesi

- Minimal 10 menit per sesi, target 30 menit total terverifikasi.
- Rekam kontinu atau potongan 3 sampai 5 menit berturut-turut.

## Perangkat

- Ponsel dengan perekam audio (44,1 atau 48 kHz, mono atau stereo).
- Perekam otomatis (AudioMoth atau sejenis) kalau tersedia.
- Catat model perangkat dan pengaturan sample rate.

## Metadata wajib per rekaman

- Tanggal dan jam mulai.
- Lokasi (koordinat atau site_id di aplikasi).
- Nama pengamat/perekam.
- Cuaca (cerah, berawan, hujan) dan kebisingan sekitar.
- Spesies yang terlihat (kalau terlihat), opsional.

## Cara unggah

1. Buka aplikasi web GemaHutan di peramban laptop atau HP.
2. Pilih situs (lokasi) yang sesuai.
3. Unggah berkas lewat `/rekam` atau `/upload`.
4. Tunggu worker memproses (BirdNET + classifier lokal).

## Cara verifikasi di aplikasi

1. Buka daftar deteksi untuk rekaman yang diunggah.
2. Putar klip deteksi dan bandingkan dengan suara asli.
3. Tandai deteksi benar/salah (peran Researcher/Admin).
4. Minimal 30 menit audio harus punya deteksi terverifikasi.

## Evaluasi

Setelah verifikasi selesai, jalankan:
```
.venv/bin/python ml/evaluasi_lapangan_asli.py
```
yang menulis `ml/reports/lapangan_asli.json` berisi menit terverifikasi,
jumlah deteksi terverifikasi, dan presisi per spesies.
