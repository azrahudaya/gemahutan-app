"""Hitung embedding Perch 2.0 untuk korpus latih GemaHutan.

Perch didistribusikan sebagai TensorFlow SavedModel dan hanya berjalan di CUDA.
Model memakai masukan 5 detik pada 32 kHz, berbeda dari pipeline BirdNET yang
memakai 3 detik pada 48 kHz, jadi audio perlu disampel ulang lebih dulu.

Keluaran ditulis ke folder terpisah supaya tidak menimpa embedding BirdNET:

    ml/embeddings_perch/embeddings.npy   (n, 1536) float32
    ml/embeddings_perch/clip_ids.json
    ml/embeddings_perch/labels.npy
    ml/embeddings_perch/label_map.json

Pemakaian:
    .venv-perch/bin/python3 ml/data/extract_perch.py --manifest ml/data/manifest_v2.csv
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np

BASE = Path(__file__).resolve().parent
REPO = BASE.parent.parent

SR_PERCH = 32000
DURASI_PERCH = 5.0
PANJANG_INPUT = int(SR_PERCH * DURASI_PERCH)
NAMA_SIGNATURE = "serving_default"


def temukan_kunci_embedding(keluaran: dict) -> str:
    """Cari nama tensor embedding 1536 dimensi di antara keluaran signature.

    Nama keluarannya bisa berbeda antar versi model, jadi dicari menurut bentuk
    tensor, bukan menurut tebakan nama.
    """
    for nama, nilai in keluaran.items():
        bentuk = tuple(nilai.shape)
        if len(bentuk) == 2 and bentuk[-1] in (1280, 1536):
            return nama
    raise KeyError(f"tensor embedding tidak ditemukan. Keluaran: {[(k, tuple(v.shape)) for k, v in keluaran.items()]}")


def baca_audio_32k(path: Path) -> np.ndarray:
    """Baca audio jadi mono 32 kHz, potong 5 detik pertama, tanpa padding.

    Sebagian berkas Xeno-canto punya header MP3 rusak sehingga librosa gagal
    dengan `LibsndfileError`. Terukur 3 berkas seperti itu di korpus v2, satu di
    tiap split. ffmpeg masih bisa menyelamatkan audionya, jadi ada fallback
    konversi ke wav sementara sebelum dibaca.
    """
    import librosa

    try:
        y, _ = librosa.load(str(path), sr=SR_PERCH, mono=True)
    except Exception:
        y = _lewat_ffmpeg(path)

    if len(y) < PANJANG_INPUT:
        y = np.pad(y, (0, PANJANG_INPUT - len(y)))
    return y[:PANJANG_INPUT].astype(np.float32)


def _lewat_ffmpeg(path: Path) -> np.ndarray:
    """Dekode berkas lewat ffmpeg lalu baca hasilnya dengan librosa.

    Dipakai hanya kalau librosa gagal. Hasilnya ditulis ke berkas sementara di
    direktori temporer sistem, bukan di dalam repo.
    """
    import subprocess
    import tempfile

    import librosa

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        keluaran = tmp.name
    try:
        subprocess.run(
            [
                "ffmpeg", "-v", "error", "-y",
                "-i", str(path),
                "-ar", str(SR_PERCH), "-ac", "1",
                keluaran,
            ],
            check=True,
            capture_output=True,
        )
        y, _ = librosa.load(keluaran, sr=SR_PERCH, mono=True)
    finally:
        Path(keluaran).unlink(missing_ok=True)
    return y


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default=str(BASE / "manifest_v2.csv"))
    parser.add_argument("--model-dir", default=str(REPO / "ml" / "models_perch"))
    parser.add_argument("--out-dir", default=str(REPO / "ml" / "embeddings_perch"))
    parser.add_argument("--batas", type=int, default=0, help="Batasi jumlah klip untuk uji cepat")
    args = parser.parse_args()

    import tensorflow as tf

    print("TensorFlow:", tf.__version__)
    gpu = tf.config.list_physical_devices("GPU")
    print("GPU:", gpu)
    if not gpu:
        raise SystemExit("Perch butuh CUDA. Jalankan skrip ini dengan venv yang punya tensorflow[and-cuda].")

    model = tf.saved_model.load(args.model_dir)
    fn = model.signatures[NAMA_SIGNATURE]

    manifest = Path(args.manifest)
    clips = list(csv.DictReader(open(manifest, encoding="utf-8")))
    if args.batas:
        clips = clips[: args.batas]

    spesies = sorted(set(c["species_scientific"] for c in clips))
    label_map = {sp: i for i, sp in enumerate(spesies)}
    print(f"Klip: {len(clips)}  Kelas: {len(label_map)}")

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    embeddings: list[np.ndarray] = []
    labels: list[int] = []
    ids: list[str] = []
    dilewati = 0
    kunci: str | None = None

    for i, clip in enumerate(clips):
        path = BASE / clip["local_path"]
        if not path.exists():
            dilewati += 1
            continue
        try:
            audio = baca_audio_32k(path)
            keluaran = fn(tf.constant(audio.reshape(1, -1)))
            if kunci is None:
                kunci = temukan_kunci_embedding(keluaran)
                print("tensor embedding:", kunci, tuple(keluaran[kunci].shape))
            emb = np.asarray(keluaran[kunci]).reshape(-1).astype(np.float32)
            embeddings.append(emb)
            labels.append(label_map[clip["species_scientific"]])
            ids.append(clip["clip_id"])
        except Exception as exc:
            dilewati += 1
            if dilewati <= 5:
                print(f"  lewat {clip['clip_id']}: {repr(exc)[:150]}")
        if (i + 1) % 250 == 0:
            print(f"  {i + 1}/{len(clips)} selesai")

    if not embeddings:
        raise SystemExit("tidak ada embedding yang berhasil dihitung")

    arr = np.stack(embeddings)
    np.save(out_dir / "embeddings.npy", arr)
    np.save(out_dir / "labels.npy", np.array(labels, dtype=np.int32))
    (out_dir / "clip_ids.json").write_text(json.dumps(ids))
    (out_dir / "label_map.json").write_text(json.dumps(label_map, indent=2))

    mean = arr.mean(axis=0)
    std = arr.std(axis=0) + 1e-8
    np.savez(out_dir / "normalization.npz", mean=mean, std=std)

    print(f"\nEmbedding: {arr.shape}  dilewati: {dilewati}")
    print("ditulis ke", out_dir)


if __name__ == "__main__":
    main()
