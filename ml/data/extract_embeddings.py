"""Extract BirdNET embeddings (1024-dim) from audio clips.
Uses the GLOBAL_AVG_POOL layer (tensor 545) from BirdNET TFLite model.
Caches to .npy files for fast training iteration.

CLI --multi-window: untuk klip >3 detik, ambil beberapa jendela dengan
stride 1.5 detik. clip_ids.json tiap jendela dibedakan dengan suffix
{clip_id}__w{index}. Untuk SOURCE training jalan dengan --multi-window
jadi n naik signifikan. Untuk SOURCE eval (evaluate_field.py) jalan
TANPA --multi-window supaya konsisten dengan inference audio live.
"""
import argparse
import csv
import json
import os
from pathlib import Path

import numpy as np

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
import warnings

warnings.filterwarnings('ignore')

BASE_DIR = Path(__file__).parent
MANIFEST = BASE_DIR / "manifest.csv"
SPLITS_FILE = BASE_DIR / "splits.json"
EMB_DIR = BASE_DIR.parent / "embeddings"

SR = 48000
DURATION = 3.0  # seconds per segment
EMBEDDING_TENSOR_INDEX = 545  # GLOBAL_AVG_POOL layer
EMBEDDING_DIM = 1024


def get_birdnet_model_path():
    """Find BirdNET TFLite model."""
    try:
        from birdnetlib.analyzer import Analyzer
        a = Analyzer()
        return a.model_path
    except Exception:
        pass
    import site
    for sp in site.getsitepackages():
        p = Path(sp) / "birdnetlib" / "models" / "analyzer" / "BirdNET_GLOBAL_6K_V2.4_Model_FP32.tflite"
        if p.exists():
            return str(p)
    raise FileNotFoundError("BirdNET model not found")


def create_interpreter(model_path):
    """Create TFLite interpreter with intermediate tensor access."""
    import tensorflow as tf
    interp = tf.lite.Interpreter(
        model_path=model_path,
        experimental_preserve_all_tensors=True,
    )
    interp.allocate_tensors()
    return interp


def load_audio_full(audio_path, sr=SR):
    """Load full audio mono pada sr target. Tidak dipotong ke 3 detik."""
    import librosa
    y, _ = librosa.load(audio_path, sr=sr, mono=True)
    return y.astype(np.float32)


def load_audio(audio_path, sr=SR, duration=DURATION):
    """Load and preprocess audio to BirdNET input format. Crop ke duration detik."""
    import librosa
    y, _ = librosa.load(audio_path, sr=sr, mono=True, duration=duration)
    target_len = int(sr * duration)
    if len(y) < target_len:
        y = np.pad(y, (0, target_len - len(y)))
    else:
        y = y[:target_len]
    return y.astype(np.float32)


def extract_birdnet_embedding(interp, audio):
    """Extract 1024-dim embedding from BirdNET GLOBAL_AVG_POOL layer."""
    input_details = interp.get_input_details()
    audio_input = audio.reshape(1, -1)
    interp.set_tensor(input_details[0]['index'], audio_input)
    interp.invoke()
    embedding = interp.get_tensor(EMBEDDING_TENSOR_INDEX)
    return embedding.reshape(-1)


def _window_slices(total_seconds: float, win_seconds: float = DURATION,
                   stride_seconds: float = 1.5, min_seconds: float = 3.0):
    """Hasilkan list (start_sec, end_sec) untuk multi-window extraction.

    Untuk klip di bawah min_seconds tidak dilakukan multi-window. Stride
    3 detik menghasilkan overlap 0% (efisien) dan biasanya cukup mengingat
    audio Xeno-canto sudah pendek.
    """
    if total_seconds < min_seconds:
        return [(0.0, min(total_seconds, win_seconds))]
    starts = []
    s = 0.0
    while s + win_seconds <= total_seconds + 1e-6:
        starts.append(s)
        s += stride_seconds
    if not starts or starts[0] > 0.0:
        starts.insert(0, 0.0)
    return [(st, st + win_seconds) for st in starts]


def main():
    parser = argparse.ArgumentParser(description="Extract BirdNET embeddings")
    parser.add_argument("--force", action="store_true",
                        help="Re-extract even if embeddings exist")
    parser.add_argument("--multi-window", action="store_true",
                        help="Untuk klip >3 detik, ambil beberapa jendela dengan stride 1.5 detik. "
                             "WINDOW_ID dibedakan dengan suffix __w{index} di clip_ids.json. "
                             "Hanya dipakai SOURCE training. Inference audio live tetap single-window.")
    parser.add_argument("--stride", type=float, default=1.5,
                        help="Stride detik antar jendela saat multi-window aktif.")
    parser.add_argument("--manifest", type=str, default="",
                        help="Berkas manifest alternatif. Kosong berarti manifest.csv.")
    parser.add_argument("--out-dir", type=str, default="",
                        help="Folder keluaran embedding. Kosong berarti ml/embeddings.")
    parser.add_argument("--ckpt-dir", type=str, default="",
                        help="Folder tempat normalization.npz ditulis. Kosong berarti "
                             "ml/checkpoints. Wajib diisi kalau memakai --out-dir supaya "
                             "normalisasi produksi tidak tertimpa.")
    args = parser.parse_args()

    manifest_path = Path(args.manifest) if args.manifest else MANIFEST
    emb_dir = Path(args.out_dir) if args.out_dir else EMB_DIR
    ckpt_dir = Path(args.ckpt_dir) if args.ckpt_dir else (EMB_DIR.parent / "checkpoints")

    emb_dir.mkdir(parents=True, exist_ok=True)

    with open(manifest_path) as f:
        clips = list(csv.DictReader(f))

    emb_file = emb_dir / "embeddings.npy"
    labels_file = emb_dir / "labels.npy"
    ids_file = emb_dir / "clip_ids.json"
    label_map_file = emb_dir / "label_map.json"
    print(f"Manifest: {manifest_path} ({len(clips)} klip)")
    print(f"Keluaran: {emb_dir}")

    # Cache key berbeda untuk multi-window agar tidak menimpa embeddings single-window.
    if emb_file.exists() and not args.force:
        existing_ids = json.loads(ids_file.read_text()) if ids_file.exists() else []
        if len(existing_ids) == len(clips) and not args.multi_window:
            print(f"Embeddings sudah diekstrak ({len(existing_ids)} klip). Pakai --force untuk re-ekstrak.")
            return
        if args.multi_window and any("__w" in cid for cid in existing_ids):
            print(f"Multi-window embeddings sudah ada ({len(existing_ids)} windows). --force untuk re-ekstrak.")
            return

    print("Loading BirdNET model...")
    model_path = get_birdnet_model_path()
    interp = create_interpreter(model_path)
    print(f"Model: {model_path}")

    species_set = sorted(set(c["species_scientific"] for c in clips))
    label_map = {sp: i for i, sp in enumerate(species_set)}
    print(f"Species: {len(label_map)} (multi-window={args.multi_window}, stride={args.stride}s)")

    embeddings = []
    labels = []
    clip_ids = []
    skipped = 0
    win_total = 0
    for i, clip in enumerate(clips):
        audio_path = BASE_DIR / clip["local_path"]
        if not audio_path.exists():
            skipped += 1
            continue
        try:
            if args.multi_window:
                y_full = load_audio_full(str(audio_path))
                total_s = len(y_full) / SR
                slices = _window_slices(total_s, stride_seconds=args.stride)
                for w_idx, (s_sec, e_sec) in enumerate(slices):
                    s_sample = int(s_sec * SR)
                    e_sample = int(e_sec * SR)
                    seg = y_full[s_sample:e_sample]
                    target_len = int(SR * DURATION)
                    if len(seg) < target_len:
                        seg = np.pad(seg, (0, target_len - len(seg)))
                    else:
                        seg = seg[:target_len]
                    emb = extract_birdnet_embedding(interp, seg.astype(np.float32))
                    embeddings.append(emb)
                    labels.append(label_map[clip["species_scientific"]])
                    clip_ids.append(f"{clip['clip_id']}__w{w_idx}")
                    win_total += 1
            else:
                audio = load_audio(str(audio_path))
                emb = extract_birdnet_embedding(interp, audio)
                embeddings.append(emb)
                labels.append(label_map[clip["species_scientific"]])
                clip_ids.append(clip["clip_id"])
        except Exception as e:
            print(f"  Error on {clip['clip_id']}: {e}")
            skipped += 1
            continue

        if (i + 1) % 100 == 0:
            print(f"  Processing {i+1}/{len(clips)} (windows: {win_total})...")

    embeddings = np.array(embeddings, dtype=np.float32)
    labels = np.array(labels, dtype=np.int32)

    np.save(emb_file, embeddings)
    np.save(labels_file, labels)
    ids_file.write_text(json.dumps(clip_ids))
    label_map_file.write_text(json.dumps(label_map, indent=2))

    mean = embeddings.mean(axis=0)
    std = embeddings.std(axis=0) + 1e-8
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    np.savez(ckpt_dir / "normalization.npz", mean=mean, std=std)

    print(f"\nExtracted {len(embeddings)} BirdNET embeddings ({EMBEDDING_DIM}-dim)")
    print(f"Classes: {len(label_map)}, Skipped: {skipped}, Multi-window: {args.multi_window}")
    print(f"Saved to {emb_dir}")
    print(f"Normalisasi: {ckpt_dir / 'normalization.npz'}")


if __name__ == "__main__":
    main()