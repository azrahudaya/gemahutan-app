"""Bangun fixture snapshot untuk test_model_snapshot.py.

Prediksi dihitung lewat EmbeddingClassifierEngine._calibrated_probs
(jalur produksi), bukan matmul manual. TFLite di-stub supaya tidak
perlu load BirdNET.

Jalankan: python3 ml/build_snapshot.py
"""

import csv
import json
import random
import shutil
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

ML = ROOT / "ml"
REPO = ROOT
CKPT = ML / "checkpoints" / "best_model.npz"
NORM = ML / "checkpoints" / "normalization.npz"
THR = ML / "reports" / "thresholds.json"
EMB_DIR = ML / "embeddings"
MANIFEST = ML / "data" / "manifest.csv"
SPLITS = ML / "data" / "splits_v3.json"

FIXTURE = ROOT / "apps" / "api" / "tests" / "fixtures" / "model_snapshots.json"
SNAPSHOT_AUDIO = ML / "tests" / "snapshot_audio"


def muat():
    """Muat model + engine (TFLite di-stub)."""
    from ml.engines.embedding_clf import EmbeddingClassifierEngine

    label_map = json.loads((ML / "checkpoints" / "label_map.json").read_text())
    inv = {v: k for k, v in label_map.items()}

    engine = EmbeddingClassifierEngine.__new__(EmbeddingClassifierEngine)
    EmbeddingClassifierEngine.__init__(engine)
    # Stub TFLite: ganti _load_birdnet_interpreter dengan no-op
    engine._load_birdnet_interpreter = lambda: None
    engine._ensure_loaded()

    return engine, label_map, inv


def pilih_10_klip():
    """Pilih 10 klip dari test split, satu per spesies folder."""
    man = {r["clip_id"]: r["local_path"]
           for r in csv.DictReader(open(MANIFEST))}
    with open(SPLITS) as f:
        sp = json.load(f)
    test_ids = sp["test"]
    from collections import defaultdict
    by_cls = defaultdict(list)
    for cid in test_ids:
        p = man.get(cid)
        if p is None:
            continue
        folder = p.split("/")[1]
        by_cls[folder].append(cid)
    kelas_unik = sorted(by_cls.keys(), key=lambda k: -len(by_cls[k]))
    random.seed(42)
    random.shuffle(kelas_unik)
    pilih = []
    for folder in kelas_unik:
        if len(pilih) >= 10:
            break
        if by_cls[folder]:
            random.seed(42)
            cid = random.choice(by_cls[folder])
            pilih.append((folder, cid))
    while len(pilih) < 10:
        for folder, lst in by_cls.items():
            if len(pilih) >= 10:
                break
            cid = lst[0]
            if not any(c[1] == cid for c in pilih):
                pilih.append((folder, cid))
    return pilih


def salin_audio(klip):
    """Salin audio klip ke folder snapshot."""
    man = {r["clip_id"]: r["local_path"]
           for r in csv.DictReader(open(MANIFEST))}
    SNAPSHOT_AUDIO.mkdir(parents=True, exist_ok=True)
    salinan = []
    for folder, cid in klip:
        src = ML / "data" / man[cid]
        dst = SNAPSHOT_AUDIO / f"{cid}.wav"
        shutil.copy(str(src), str(dst))
        salinan.append({
            "clip_id": cid,
            "species_folder": folder,
            "audio_path": str(dst.relative_to(REPO)),
        })
    return salinan


def prediksi_dengan_engine(klip, engine, label_map, inv):
    """Prediksi lewat EmbeddingClassifierEngine._calibrated_probs."""
    thr = json.loads(THR.read_text())
    emb_all = np.load(EMB_DIR / "embeddings.npy")
    with open(EMB_DIR / "clip_ids.json") as f:
        ids = json.load(f)

    out = []
    for folder, cid in klip:
        if cid not in ids:
            continue
        i = ids.index(cid)
        emb = emb_all[i]
        emb_norm = ((emb.reshape(1, -1) - engine._mean) / engine._std).astype(np.float32)

        # Jalur produksi: _calibrated_probs
        probs = engine._calibrated_probs(emb_norm)[0]

        # Threshold filtering (like production + snapshot test)
        diizinkan = [c for c, nama in enumerate(label_map)
                     if probs[c] >= thr.get(nama, 0.0)]
        if not diizinkan:
            diizinkan = [int(np.argmax(probs))]
        pred_idx = diizinkan[np.argmax(probs[diizinkan])]

        out.append({
            "clip_id": cid,
            "species_folder": folder,
            "embedding": emb.tolist(),
            "expected_label": inv[pred_idx],
            "expected_confidence": float(probs[pred_idx]),
        })
    return out


def main():
    SNAPSHOT_AUDIO.mkdir(parents=True, exist_ok=True)
    FIXTURE.parent.mkdir(parents=True, exist_ok=True)

    print("Memuat engine produksi...")
    engine, label_map, inv = muat()

    klip = pilih_10_klip()
    print(f"Pilih {len(klip)} klip:")
    for folder, cid in klip:
        print(f"  {folder:30s} {cid}")

    audio_meta = salin_audio(klip)
    preds = prediksi_dengan_engine(klip, engine, label_map, inv)

    pred_map = {p["clip_id"]: p for p in preds}
    snapshot_clips = []
    for a in audio_meta:
        p = pred_map[a["clip_id"]]
        snapshot_clips.append({
            "clip_id": a["clip_id"],
            "species_folder": a["species_folder"],
            "audio_path": a["audio_path"],
            "embedding": p["embedding"],
            "expected_label": p["expected_label"],
            "expected_confidence": p["expected_confidence"],
        })

    snapshot_doc = {
        "version": 3,
        "model": "ml/checkpoints/best_model.npz",
        "thresholds": "ml/reports/thresholds.json",
        "normalization": "ml/checkpoints/normalization.npz",
        "temperature": float(engine._temperature),
        "bias": engine._bias.tolist() if engine._bias is not None else None,
        "tolerance": 1e-3,
        "engine": "EmbeddingClassifierEngine._calibrated_probs",
        "clips": snapshot_clips,
    }
    FIXTURE.write_text(json.dumps(snapshot_doc, indent=2))
    print(f"\n  tulis {FIXTURE}")
    print(f"  salin {len(snapshot_clips)} audio ke {SNAPSHOT_AUDIO}")


if __name__ == "__main__":
    main()