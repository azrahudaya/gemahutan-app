# Model Selection Report -- GemaHutan

## Kandidat yang Dievaluasi

| Model | Format | Ukuran | Lisensi | GPU? | Tersedia? | Latensi (3s audio, CPU) |
|-------|--------|--------|---------|------|-----------|------------------------|
| BirdNET-Analyzer v2.4 | TFLite | ~20 MB | CC BY-NC-SA 4.0 | Tidak | Ya (pip install birdnetlib) | ~1-2 detik |
| Google Perch v2 | TF SavedModel | ~80 MB | Apache 2.0 | Opsional | Ya (Kaggle, HuggingFace) | ~3-5 detik |
| YAMNet | TFLite | ~4 MB | Apache 2.0 | Tidak | Ya (TF Hub) | ~0.5 detik |
| BEATs | PyTorch | ~90 MB | MIT | Opsional | Ya (GitHub/HuggingFace) | ~4-6 detik |
| AudioMAE | PyTorch | ~300 MB | CC BY-NC 4.0 | Ya | Ya (GitHub) | ~8 detik |

## Hasil Pengujian Nyata

### BirdNET-Analyzer v2.4
- Diinstal via `pip install birdnetlib` + `tensorflow-cpu`
- Model TFLite dimuat otomatis oleh library
- Inference pada audio 3 detik (440 Hz pure tone): 0 deteksi (benar, bukan suara burung)
- 6522 spesies didukung secara global
- Filter lokasi Indonesia membatasi ke ~514 spesies relevan
- CPU-only, tanpa GPU

### Google Perch v2
- Tersedia di Kaggle (google/bird-vocalization-classifier) dan HuggingFace (tphakala/Perch-v2)
- Membutuhkan akun Kaggle untuk download dari Kaggle (dicatat di NEEDS_FROM_YOU.md)
- Embedding berkualitas tinggi untuk transfer learning (Track B)
- Lebih berat dari BirdNET

### YAMNet
- Classifier generik AudioSet (521 kelas)
- Hanya 2 kelas burung generik, tidak spesifik spesies
- Cocok untuk pembanding ablation, bukan untuk deteksi spesies

### BEATs / AudioMAE
- Embedding model bagus untuk transfer learning
- Lebih berat, butuh PyTorch
- Tidak langsung memberikan deteksi per-spesies

## Keputusan

**Track A (Zero-shot baseline): BirdNET-Analyzer v2.4**

Alasan:
1. Satu-satunya yang langsung memberikan deteksi per-spesies tanpa training
2. CPU-friendly, ringan (~20 MB model)
3. 6522 spesies global, termasuk spesies Indonesia
4. Library Python siap pakai (birdnetlib)
5. Paper #1 dan #20 membahas BirdNET sebagai baseline bioakustik

Keterbatasan yang diketahui (paper #9, #20):
- Akurasi turun untuk spesies lokal yang jarang di data latih
- Skor confidence BUKAN probabilitas terkalibrasi
- Perlu threshold per-spesies, bukan satu threshold global

**Track B (Transfer learning): akan menggunakan embedding dari BirdNET + classifier lokal**
- BirdNET embedding (layer kedua dari belakang) + MLP classifier untuk spesies Indonesia
- Alternatif: Perch v2 kalau embedding BirdNET kurang bagus

**Fallback:** StubEngine tersedia untuk menjalankan pipeline tanpa model asli.

## File terkait
- `ml/engines/base.py` -- interface InferenceEngine
- `ml/engines/birdnet.py` -- BirdNetEngine (Track A)
- `ml/engines/stub.py` -- StubEngine (fallback)
- `ml/engines/embedding_clf.py` -- EmbeddingClassifierEngine (Track B, Fase 9)
