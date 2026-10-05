"""Generate synthetic bird-like audio dataset for pipeline testing.
Used as workaround when Xeno-canto API key is not available.
Each species gets distinct frequency patterns to simulate real variation."""
import csv
import hashlib
import json
from pathlib import Path

import numpy as np
import soundfile as sf

BASE_DIR = Path(__file__).parent
AUDIO_DIR = BASE_DIR / "audio"
MANIFEST = BASE_DIR / "manifest.csv"
SPECIES_FILE = BASE_DIR / "species_list.json"

SR = 48000
CLIP_DURATION = 5.0  # seconds


def generate_bird_call(species_idx: int, clip_idx: int, sr=SR, duration=CLIP_DURATION):
    """Generate synthetic bird-like audio with species-specific frequency patterns."""
    np.random.seed(species_idx * 1000 + clip_idx)
    t = np.linspace(0, duration, int(sr * duration))

    # Species-specific base frequency (2000-8000 Hz range)
    base_freq = 2000 + (species_idx * 200) % 6000

    # Generate chirp-like calls
    audio = np.zeros_like(t)
    num_calls = np.random.randint(3, 8)

    for _ in range(num_calls):
        start = np.random.uniform(0, duration - 0.5)
        call_dur = np.random.uniform(0.1, 0.5)
        mask = (t >= start) & (t < start + call_dur)

        freq_start = base_freq + np.random.uniform(-500, 500)
        freq_end = freq_start + np.random.uniform(-1000, 1000)
        freqs = np.linspace(freq_start, freq_end, mask.sum())

        phase = np.cumsum(2 * np.pi * freqs / sr)
        call = 0.3 * np.sin(phase)

        # Envelope
        env_len = len(call)
        envelope = np.ones(env_len)
        attack = min(int(0.01 * sr), env_len // 4)
        decay = min(int(0.02 * sr), env_len // 4)
        if attack > 0:
            envelope[:attack] = np.linspace(0, 1, attack)
        if decay > 0:
            envelope[-decay:] = np.linspace(1, 0, decay)

        call *= envelope

        # Add harmonics
        if np.random.random() > 0.3:
            phase2 = np.cumsum(2 * np.pi * freqs * 2 / sr)
            call += 0.1 * np.sin(phase2) * envelope

        audio[mask] += call

    # Add background noise
    audio += np.random.normal(0, 0.02, len(audio))

    # Normalize
    peak = np.max(np.abs(audio))
    if peak > 0:
        audio = audio / peak * 0.8

    return audio


def generate_negative(clip_idx: int, sr=SR, duration=CLIP_DURATION):
    """Generate negative samples: wind, rain, insects, silence."""
    np.random.seed(90000 + clip_idx)
    t = np.linspace(0, duration, int(sr * duration))

    noise_type = clip_idx % 4
    if noise_type == 0:  # Wind
        audio = np.random.normal(0, 0.1, len(t))
        # Low-pass effect
        from scipy.signal import butter, sosfilt
        sos = butter(4, 500, btype='low', fs=sr, output='sos')
        audio = sosfilt(sos, audio)
    elif noise_type == 1:  # Rain
        audio = np.random.normal(0, 0.15, len(t))
        from scipy.signal import butter, sosfilt
        sos = butter(4, [200, 8000], btype='band', fs=sr, output='sos')
        audio = sosfilt(sos, audio)
    elif noise_type == 2:  # Insects (high freq buzz)
        freq = np.random.uniform(4000, 10000)
        audio = 0.05 * np.sin(2 * np.pi * freq * t)
        audio *= (1 + 0.5 * np.sin(2 * np.pi * 10 * t))  # amplitude modulation
        audio += np.random.normal(0, 0.02, len(t))
    else:  # Near-silence
        audio = np.random.normal(0, 0.005, len(t))

    peak = np.max(np.abs(audio))
    if peak > 0:
        audio = audio / peak * 0.5
    return audio


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    with open(SPECIES_FILE) as f:
        species_list = json.load(f)

    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    clips = []
    clips_per_species = 50

    # Generate bird species clips
    for sp_idx, sp in enumerate(species_list):
        sci = sp["scientific_name"]
        sp_dir = AUDIO_DIR / sci.replace(" ", "_")
        sp_dir.mkdir(parents=True, exist_ok=True)
        print(f"[{sp_idx+1}/{len(species_list)}] {sci}")

        for clip_idx in range(clips_per_species):
            clip_id = f"synth-{sci.replace(' ', '_')}-{clip_idx:03d}"
            filename = f"{clip_id}.wav"
            filepath = sp_dir / filename

            if not filepath.exists():
                audio = generate_bird_call(sp_idx, clip_idx)
                sf.write(str(filepath), audio, SR)

            sha = sha256_file(filepath)
            clips.append({
                "clip_id": clip_id,
                "source": "synthetic",
                "source_url": "",
                "species_scientific": sci,
                "species_common": sp.get("common_name", ""),
                "split": "",
                "duration_s": CLIP_DURATION,
                "sample_rate": SR,
                "quality": "synthetic",
                "license": "MIT",
                "sha256": sha,
                "local_path": str(filepath.relative_to(BASE_DIR)),
            })

    # Generate negative samples
    neg_dir = AUDIO_DIR / "_negative"
    neg_dir.mkdir(parents=True, exist_ok=True)
    num_negatives = 300
    print(f"Generating {num_negatives} negative samples...")

    for clip_idx in range(num_negatives):
        clip_id = f"synth-negative-{clip_idx:03d}"
        filename = f"{clip_id}.wav"
        filepath = neg_dir / filename

        if not filepath.exists():
            audio = generate_negative(clip_idx)
            sf.write(str(filepath), audio, SR)

        sha = sha256_file(filepath)
        clips.append({
            "clip_id": clip_id,
            "source": "synthetic",
            "source_url": "",
            "species_scientific": "_negative",
            "species_common": "negative",
            "split": "",
            "duration_s": CLIP_DURATION,
            "sample_rate": SR,
            "quality": "synthetic",
            "license": "MIT",
            "sha256": sha,
            "local_path": str(filepath.relative_to(BASE_DIR)),
        })

    # Write manifest
    fieldnames = [
        "clip_id", "source", "source_url", "species_scientific", "species_common",
        "split", "duration_s", "sample_rate", "quality", "license", "sha256", "local_path",
    ]
    with open(MANIFEST, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for c in clips:
            writer.writerow({k: c.get(k, "") for k in fieldnames})

    print(f"\nTotal: {len(clips)} clips ({len(species_list)} species x {clips_per_species} + {num_negatives} negatives)")
    print(f"Manifest: {MANIFEST}")


if __name__ == "__main__":
    main()
