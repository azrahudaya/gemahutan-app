"""Ekstrak embedding BirdNET dari JENDELA BERSURARA, bukan 3 detik pertama.

Perbaikan untuk butir 8: label tidak asal 3 detik pertama.

Pendekatan:
1. Muat audio PENUH (bukan dipotong ke 3 detik)
2. Bagi menjadi jendela 3 detik dengan stride
3. Filter jendela sepi (energi RMS di bawah ambang) -> buang
4. Labeli jendela tersisa dengan spesies klip

Output: embeddings.npy, labels.npy, clip_ids.json, label_map.json
Format identik dengan extract_embeddings.py supaya kompatibel dengan train loop.

Jalankan:
  source .venv/bin/activate && python ml/extract_jendela_bersuara.py

Opsi:
  --stride 1.5      Jarak antar jendela (detik)
  --energi-min 0.01  Ambang RMS minimum (0-1), default 0.01
  --out-dir DIR     Folder output (default: ml/embeddings_bersuara)
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
ML_DIR = ROOT / "ml"
MANIFEST_DEFAULT = ML_DIR / "data" / "manifest_v2.csv"
EMB_DIR_DEFAULT = ML_DIR / "embeddings_bersuara"

SR = 48000
DURATION = 3.0  # detik per jendela
EMBEDDING_TENSOR_INDEX = 545
EMBEDDING_DIM = 1024


def get_birdnet_model_path() -> str:
    try:
        from birdnetlib.analyzer import Analyzer
        return Analyzer().model_path
    except Exception:
        pass
    import site
    for sp in site.getsitepackages():
        p = Path(sp) / "birdnetlib" / "models" / "analyzer" / \
            "BirdNET_GLOBAL_6K_V2.4_Model_FP32.tflite"
        if p.exists():
            return str(p)
    raise FileNotFoundError("BirdNET model not found")


def muat_audio_full(path: str) -> np.ndarray:
    """Muat audio penuh, mono, 48 kHz.

    librosa/soundfile TIDAK bisa membaca m4a/aac ("Format not recognised"),
    jadi perlu jalur cadangan ffmpeg. Tanpa ini ekstraksi uji independen gagal
    pada 35 dari 135 klip, dan kegagalannya TIDAK acak: seluruhnya m4a (34)
    plus mpga (2), yaitu rekaman ponsel iNaturalist. Menghitung gerbang dari
    100 klip sisanya akan membuang justru subset tersulit dan memberi angka
    optimistis palsu.
    """
    import librosa
    try:
        y, _ = librosa.load(path, sr=SR, mono=True)
        return y.astype(np.float32)
    except Exception:
        pass

    import subprocess
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        wav = str(Path(tmp) / "konversi.wav")
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", str(path),
             "-ar", str(SR), "-ac", "1", wav],
            check=True, timeout=180, capture_output=True,
        )
        y, _ = librosa.load(wav, sr=SR, mono=True)
        return y.astype(np.float32)


def rms_energy(y: np.ndarray) -> float:
    """Root mean square energy dari sinyal."""
    if len(y) == 0:
        return 0.0
    return float(np.sqrt(np.mean(y ** 2)))


def jendela_bersuara(
    y_full: np.ndarray,
    stride_s: float = 1.5,
    energi_min: float = 0.01,
) -> list[tuple[int, int, float]]:
    """Bagi audio penuh jadi jendela 3 detik, return yang punya energi cukup.

    Returns: list of (start_sample, end_sample, rms)
    """
    win_samples = int(SR * DURATION)
    stride_samples = int(SR * stride_s)
    total = len(y_full)

    hasil = []
    s = 0
    while s + win_samples <= total:
        seg = y_full[s:s + win_samples]
        rms = rms_energy(seg)
        if rms >= energi_min:
            hasil.append((s, s + win_samples, round(rms, 6)))
        s += stride_samples

    # Jangan lupa jendela terakhir (mungkin < 3 detik, tapi tetap diambil
    # kalau cukup panjang)
    if total > s and total - s >= int(SR * 1.0):
        seg = y_full[s:total]
        rms = rms_energy(seg)
        if rms >= energi_min:
            # Pad ke 3 detik
            hasil.append((s, total, round(rms, 6)))

    return hasil


def ekstrak_embedding(interp, audio_seg: np.ndarray) -> np.ndarray:
    """Ekstrak embedding 1024-dim dari segmen audio."""
    target_len = int(SR * DURATION)
    if len(audio_seg) < target_len:
        audio_seg = np.pad(audio_seg, (0, target_len - len(audio_seg)))
    else:
        audio_seg = audio_seg[:target_len]

    input_details = interp.get_input_details()
    audio_input = audio_seg.reshape(1, -1)
    interp.set_tensor(input_details[0]["index"], audio_input)
    interp.invoke()
    return interp.get_tensor(EMBEDDING_TENSOR_INDEX).reshape(-1)


def main() -> int:
    import os
    os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

    parser = argparse.ArgumentParser(description="Ekstrak embedding dari jendela bersuara")
    parser.add_argument("--stride", type=float, default=1.5,
                        help="Stride antar jendela (detik)")
    parser.add_argument("--energi-min", type=float, default=0.01,
                        help="Ambang RMS minimum (0-1)")
    parser.add_argument("--out-dir", type=str, default=str(EMB_DIR_DEFAULT),
                        help="Folder output embedding")
    parser.add_argument("--manifest", type=str, default=str(MANIFEST_DEFAULT),
                        help="Path manifest CSV")
    parser.add_argument("--force", action="store_true",
                        help="Re-ekstrak meski embedding sudah ada")
    args = parser.parse_args()

    emb_dir = Path(args.out_dir)
    emb_dir.mkdir(parents=True, exist_ok=True)

    emb_file = emb_dir / "embeddings.npy"
    ids_file = emb_dir / "clip_ids.json"
    labels_file = emb_dir / "labels.npy"
    label_map_file = emb_dir / "label_map.json"

    if emb_file.exists() and not args.force:
        existing = json.loads(ids_file.read_text()) if ids_file.exists() else []
        print(f"Embedding sudah ada ({len(existing)} jendela). --force untuk re-ekstrak.")
        return 0

    # Baca manifest
    with open(args.manifest) as f:
        clips = list(csv.DictReader(f))

    print(f"Manifest: {args.manifest} ({len(clips)} klip)")
    print(f"Stride: {args.stride}s, Energi min: {args.energi_min}")

    # Muat BirdNET
    import tensorflow as tf
    print("Loading BirdNET model...")
    model_path = get_birdnet_model_path()
    interp = tf.lite.Interpreter(
        model_path=model_path,
        experimental_preserve_all_tensors=True,
    )
    interp.allocate_tensors()

    species_set = sorted(set(c["species_scientific"] for c in clips))
    label_map = {sp: i for i, sp in enumerate(species_set)}
    print(f"Species: {len(label_map)}")

    embeddings = []
    labels = []
    clip_ids = []
    skipped = 0
    total_jendela = 0
    jendela_sepi = 0

    audio_base = ML_DIR / "data"

    for i, clip in enumerate(clips):
        local_path = clip.get("local_path", "")
        audio_path = audio_base / local_path
        if not audio_path.exists():
            skipped += 1
            continue

        try:
            y_full = muat_audio_full(str(audio_path))
            jendela = jendela_bersuara(y_full, args.stride, args.energi_min)

            total_durasi = len(y_full) / SR
            total_jendela += int(total_durasi / args.stride)

            if not jendela:
                jendela_sepi += 1
                # Fallback: ambil 3 detik pertama supaya klip tidak hilang
                seg = y_full[:int(SR * DURATION)]
                if len(seg) < int(SR * DURATION):
                    seg = np.pad(seg, (0, int(SR * DURATION) - len(seg)))
                emb = ekstrak_embedding(interp, seg)
                embeddings.append(emb)
                labels.append(label_map[clip["species_scientific"]])
                clip_ids.append(f"{clip['clip_id']}__w0")
                continue

            for w_idx, (s_samp, e_samp, _rms) in enumerate(jendela):
                seg = y_full[s_samp:e_samp]
                emb = ekstrak_embedding(interp, seg)
                embeddings.append(emb)
                labels.append(label_map[clip["species_scientific"]])
                clip_ids.append(f"{clip['clip_id']}__w{w_idx}")

        except Exception as e:
            print(f"  Error {clip['clip_id']}: {e}")
            skipped += 1
            continue

        if (i + 1) % 200 == 0:
            print(f"  [{i+1}/{len(clips)}] {len(embeddings)} jendela, "
                  f"{jendela_sepi} klip sepi")

    embeddings = np.array(embeddings, dtype=np.float32)
    labels_arr = np.array(labels, dtype=np.int32)

    np.save(emb_file, embeddings)
    np.save(labels_file, labels_arr)
    ids_file.write_text(json.dumps(clip_ids))
    label_map_file.write_text(json.dumps(label_map, indent=2))

    print("\nHasil:")
    print(f"  Klip diproses: {len(clips) - skipped}")
    print(f"  Gagal/skip: {skipped}")
    print(f"  Jendela total: {len(embeddings)}")
    print(f"  Klip sepi (fallback 3s): {jendela_sepi}")
    print(f"  Output: {emb_dir}")
    print(f"  embeddings.npy: {embeddings.shape}")
    print(f"  labels.npy: {labels_arr.shape}, kelas: {len(label_map)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())