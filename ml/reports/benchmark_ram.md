# Benchmark RAM dan Latensi (butir 7)

Dijalankan 28 Sep 2026. Tujuan: rekaman 60 menit hemat RAM, benchmark sungguhan.

Berkas uji: `ml/data/bench_60min.mp3` (57,6 MB, 60,00 menit, 44,1 kHz mono).

## Akar masalah

`ml/engines/embedding_clf.py` memuat SELURUH audio dengan
`librosa.load(audio_path, sr=48000, mono=True)` sebelum memotong jadi segmen.
Rekaman 60 menit @ 48 kHz float32 = 691 MB array, ditambah buffer resampling
librosa (2,1 GB peak). Karena cascade memanggil BirdNET + Track B + indeks
akustik, audio dimuat berkali-kali, RAM menembus 3,9 GB.

## Perbaikan

`ml/engines/streaming.py` baru: pembaca streaming yang memakai
`soundfile.SoundFile.seek/read` untuk membaca SATU jendela per waktu, lalu
resample per jendela (scipy `resample_poly`). Tidak pernah memuat file penuh.

`ml/engines/embedding_clf.py` `predict()` dan `predict_embedding()` sekarang
memakai `segmen_stream()` alih-alih `librosa.load()` penuh.

## Hasil pengukuran

### Muat audio saja (60 menit)

| Metode | Peak RSS | Waktu |
|--------|----------|-------|
| Lama (librosa full load) | 2100 MB | 4,2 s |
| Baru (streaming) | 31 MB | 2,8 s |

Turun 67x, dan lebih cepat.

### Track B penuh (1800 segmen embedding)

| Metrik | Nilai |
|--------|-------|
| Peak RSS | 963 MB |
| Waktu | 55,1 s |
| Kecepatan | 65,3x realtime |

Peak RSS 963 MB didominasi model TFLite BirdNET (857 MB, biaya tetap karena
`experimental_preserve_all_tensors=True` untuk akses layer embedding), bukan
audio.

### Cascade penuh (BirdNET + Track B, 60 menit)

| Metrik | Nilai |
|--------|-------|
| Peak RSS | 2921 MB (2,9 GB) |
| Waktu | 95,3 s |
| Kecepatan | 37,8x realtime |

Turun dari 3,9 GB. Sisa 2,9 GB sebagian besar dari `birdnetlib.Recording`
yang masih memuat audio penuh via `librosa.load` di `read_audio_data()`.

## Sisa pekerjaan

BirdNET (Track A) masih memuat audio penuh. `birdnetlib.Recording.read_audio_data`
memakai `librosa.load(path, sr=SAMPLE_RATE, ...)`. Untuk turun di bawah 1 GB,
BirdNetEngine perlu streaming per 3 detik lewat `Analyzer.predict(sample)`,
bukan `Recording.analyze()`. Belum dikerjakan.

## Paritas (streaming vs lama)

Uji pada 44 segmen klip 87,6 detik:

- Jumlah segmen: identik (44)
- Posisi start: identik
- Argmax prediksi: 44/44 sama
- Keyakinan top-1: beda maksimum 0,0001 (pembulatan float resampling)

Output model efektif identik, RAM turun drastis.

## Perintah uji ulang

```bash
source .venv/bin/activate
python -m ml.engines.streaming ml/data/bench_60min.mp3
```