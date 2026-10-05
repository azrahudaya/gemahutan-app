"""Pilih jendela latih untuk setiap klip (label lemah -> jendela kuat).

Membaca hasil multi-window extraction (embeddings_v4) dan memilih jendela
terbaik per klip dengan salah satu aturan, hanya memakai label KLIP (bukan
label jendela yang tidak ada):

- "energi": pilih k jendela dengan energi (RMS) tertinggi. k default 1.
- "birdnet": pilih jendela yang skor BirdNET untuk spesies label >= x.

Aturan dan parameter (k, x) dipilih lewat CV dalam di evaluasi_bersarang.py.
Evaluasi tetap tingkat klip: skor klip = maks jendela (sama dengan produksi).

Keluaran: embeddings_v4/embeddings_terpilih.npy, labels_terpilih.npy,
clip_ids_terpilih.json, pemilihan_jendela.json.

Jalankan: .venv/bin/python ml/pilih_jendela.py --metode energi --k 1
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
DATA_DIR = ML_DIR / "data"
SR = 48000
SEGMENT = 3.0


def energy_segmen(y: np.ndarray, start_sample: int, seg_len: int) -> float:
    seg = y[start_sample:start_sample + seg_len]
    if len(seg) == 0:
        return 0.0
    return float(np.sqrt(np.mean(seg.astype(np.float64) ** 2)))


def parse_durasi(s: str) -> float:
    s = (s or "").strip()
    if ":" in s:
        m, sec = s.split(":")
        return int(m) * 60 + float(sec)
    try:
        return float(s)
    except ValueError:
        return 0.0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--emb-dir", default=str(ML_DIR / "embeddings_v4"))
    ap.add_argument("--metode", choices=["energi", "birdnet"], default="energi")
    ap.add_argument("--k", type=int, default=1)
    ap.add_argument("--x", type=float, default=0.5, help="ambang skor BirdNET (metode birdnet)")
    ap.add_argument("--stride", type=float, default=1.5)
    args = ap.parse_args()

    emb_dir = Path(args.emb_dir)
    emb_file = emb_dir / "embeddings.npy"
    labels_file = emb_dir / "labels.npy"
    ids_file = emb_dir / "clip_ids.json"
    if not (emb_file.exists() and ids_file.exists()):
        print("embeddings_v4 belum diekstrak. Jalankan extract_embeddings.py --multi-window dulu.",
              file=sys.stderr)
        return 2

    X = np.load(emb_file)
    y = np.load(labels_file)
    ids = json.loads(ids_file.read_text())

    # Kelompokkan jendela per klip.
    from collections import defaultdict
    jendela_per_klip = defaultdict(list)  # clip_id -> list indeks di X
    for i, cid in enumerate(ids):
        # "{clip}__w{i}" -> clip = bagian sebelum "__w"
        clip = cid.rsplit("__w", 1)[0]
        jendela_per_klip[clip].append(i)

    # Hitung energi per jendela (butuh audio, sekali per klip).
    manifest = {r["clip_id"]: r for r in csv.DictReader((DATA_DIR / "manifest_v2.csv").open())}
    seg_len = int(SR * SEGMENT)
    step = int(SR * args.stride)

    terpilih = []
    label_terpilih = []
    id_terpilih = []
    ringkasan = {"metode": args.metode, "k": args.k, "x": args.x,
                 "emb_dir": str(emb_dir),
                 "n_klip": 0, "n_jendela_total": len(ids), "n_jendela_terpilih": 0}

    import librosa
    for clip, idxs in sorted(jendela_per_klip.items()):
        rec = manifest.get(clip)
        if not rec:
            continue
        berkas = DATA_DIR / rec["local_path"]
        if not berkas.exists():
            continue
        try:
            y_full = librosa.load(str(berkas), sr=SR, mono=True)[0].astype(np.float32)
        except Exception:
            continue

        # Energi tiap jendela milik klip ini.
        skor = []
        for i in idxs:
            w = int(ids[i].rsplit("__w", 1)[1])  # nomor jendela
            start = w * step
            skor.append((energy_segmen(y_full, start, seg_len), i))

        if args.metode == "energi":
            # k jendela energi tertinggi.
            skor.sort(key=lambda t: -t[0])
            dipilih = [i for _, i in skor[: max(1, args.k)]]
        else:
            # birdnet: skor >= x; fallback jendela energi tertinggi kalau tak ada.
            dipilih = [i for s, i in skor if s >= args.x]
            if not dipilih:
                dipilih = [max(skor, key=lambda t: t[0])[1]]

        for i in dipilih:
            terpilih.append(X[i])
            label_terpilih.append(y[i])
            id_terpilih.append(ids[i])

    Xt = np.array(terpilih, dtype=np.float32) if terpilih else np.zeros((0, X.shape[1]), np.float32)
    yt = np.array(label_terpilih, dtype=np.int32) if label_terpilih else np.array([], np.int32)

    np.save(emb_dir / "embeddings_terpilih.npy", Xt)
    np.save(emb_dir / "labels_terpilih.npy", yt)
    (emb_dir / "clip_ids_terpilih.json").write_text(json.dumps(id_terpilih))

    ringkasan["n_klip"] = len(jendela_per_klip)
    ringkasan["n_jendela_terpilih"] = len(id_terpilih)
    out = ML_DIR / "reports" / "pemilihan_jendela.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(ringkasan, indent=2, ensure_ascii=False))
    print(json.dumps(ringkasan, indent=2, ensure_ascii=False))
    print(f"Tersimpan: {emb_dir}/embeddings_terpilih.npy ({len(id_terpilih)} jendela)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
