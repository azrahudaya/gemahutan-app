"""Evaluasi model berbasis embedding Perch pada korpus lapangan GemaHutan.

`ml/evaluate_field.py` tidak bisa dipakai untuk model Perch karena skrip itu
menghitung embedding dengan BirdNET, yang berdimensi 1024. Bobot model Perch
berbentuk (1536, 256), jadi masukannya harus embedding Perch.

Skrip ini meniru logika penilaian yang sama supaya angkanya bisa dibandingkan
langsung dengan laporan BirdNET:

- pemotongan jendela dengan tumpang tindih 50 persen dan batas jendela per berkas
- akurasi top-1 dan macro F1 dari argmax
- tingkat deteksi memakai ambang per spesies
- deteksi palsu pada kelompok pengecoh

Bedanya hanya sumber embedding dan panjang jendela: Perch memakai 5 detik pada
32 kHz, sedangkan BirdNET 3 detik pada 48 kHz.

Pemakaian:
    .venv-perch/bin/python3 ml/evaluate_perch.py --checkpoint-dir ml/checkpoints_perch
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

BASE = Path(__file__).resolve().parent
REPO = BASE.parent
DATA = BASE / "data"

SR = 32000
DURASI = 5.0
PANJANG = int(SR * DURASI)
AMBANG_SENYAP = 1e-4
ML_DIR = BASE
REPORTS = ML_DIR / "reports"


def baca_audio(berkas: Path):
    """Baca audio mono pada 32 kHz, dengan fallback ffmpeg."""
    import librosa

    try:
        y, _ = librosa.load(str(berkas), sr=SR, mono=True)
        return y
    except Exception:
        pass
    with tempfile.TemporaryDirectory() as tmp:
        tujuan = Path(tmp) / "audio.wav"
        subprocess.run(
            ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
             "-i", str(berkas), "-ar", str(SR), "-ac", "1", str(tujuan)],
            capture_output=True, check=True,
        )
        y, _ = librosa.load(str(tujuan), sr=SR, mono=True)
    return y


def jendela_audio(berkas: Path, maks_jendela: int) -> list[np.ndarray]:
    """Potong jadi jendela 5 detik dengan tumpang tindih 50 persen."""
    try:
        y = baca_audio(berkas)
    except Exception as exc:
        print(f"    gagal baca {berkas.name}: {str(exc)[:60]}")
        return []

    langkah = PANJANG // 2 or PANJANG
    hasil = []
    for mulai in range(0, max(1, len(y) - PANJANG + 1), langkah):
        potong = y[mulai : mulai + PANJANG]
        if len(potong) < PANJANG:
            potong = np.pad(potong, (0, PANJANG - len(potong)))
        if float(np.sqrt(np.mean(potong ** 2))) < AMBANG_SENYAP:
            continue
        hasil.append(potong.astype(np.float32))
        if len(hasil) >= maks_jendela:
            break
    return hasil


def hitung_embedding(fn, kunci, berkas_list: list[Path], maks_jendela: int):
    """Hitung embedding Perch untuk semua jendela dari daftar berkas."""
    import tensorflow as tf

    fitur, sumber = [], []
    for berkas in berkas_list:
        for jendela in jendela_audio(berkas, maks_jendela):
            keluaran = fn(tf.constant(jendela.reshape(1, -1)))
            fitur.append(np.asarray(keluaran[kunci]).reshape(-1).astype(np.float32))
            sumber.append(berkas.name)
    return np.array(fitur, dtype=np.float32), sumber


def metrik(y_true, probs, inv_map, thresholds, kelas_target) -> dict:
    preds = np.argmax(probs, axis=1)
    akurasi = float(np.mean(preds == y_true)) if len(y_true) else 0.0
    f1s = []
    for cls in sorted({int(c) for c in y_true if int(c) in kelas_target}):
        benar, tebak = y_true == cls, preds == cls
        tp = int(np.sum(benar & tebak))
        fp = int(np.sum(~benar & tebak))
        fn = int(np.sum(benar & ~tebak))
        presisi = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1s.append(2 * presisi * recall / (presisi + recall) if presisi + recall else 0.0)
    ambang = np.array([thresholds.get(inv_map[c], 0.5) for c in range(probs.shape[1])])
    lewat = probs >= ambang
    mask = np.zeros(probs.shape[1], dtype=bool)
    mask[kelas_target] = True
    deteksi = float(np.mean(np.any(lewat[:, mask], axis=1))) if len(y_true) else 0.0
    return {
        "jumlah_jendela": int(len(y_true)),
        "akurasi_top1": round(akurasi, 4),
        "macro_f1": round(float(np.mean(f1s)), 4) if f1s else 0.0,
        "kelas_dinilai": len(f1s),
        "tingkat_deteksi": round(deteksi, 4),
    }


def deteksi_palsu(probs, inv_map, thresholds, kelas_target) -> float:
    if not len(probs):
        return 0.0
    ambang = np.array([thresholds.get(inv_map[c], 0.5) for c in range(probs.shape[1])])
    mask = np.zeros(probs.shape[1], dtype=bool)
    mask[kelas_target] = True
    return round(float(np.mean(np.any((probs >= ambang) & mask, axis=1))), 4)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint-dir", default=str(ML_DIR / "checkpoints_perch"))
    parser.add_argument("--akhiran", default="_perch")
    parser.add_argument("--maks-jendela", type=int, default=8)
    args = parser.parse_args()

    sys.path.insert(0, str(REPO))
    from ml.train import MLP

    ckpt_dir = Path(args.checkpoint_dir)
    ckpt = ckpt_dir / "best_model.npz"
    norm = ckpt_dir / "normalization.npz"
    if not ckpt.exists():
        print("checkpoint tidak ada:", ckpt)
        return 1

    label_map = json.loads((ML_DIR / "embeddings_perch" / "label_map.json").read_text())
    inv_map = {v: k for k, v in label_map.items()}
    thresholds = json.loads((REPORTS / "thresholds.json").read_text())

    n = np.load(norm)
    mean, std = n["mean"], n["std"]
    model = MLP(len(mean), 256, len(label_map))
    model.load(str(ckpt))
    model.training = False

    import tensorflow as tf

    print("Memuat model Perch...")
    perch = tf.saved_model.load(str(ML_DIR / "models_perch"))
    fn = perch.signatures["serving_default"]

    # Cari nama tensor embedding sekali saja memakai satu jendela senyap.
    uji = fn(tf.constant(np.zeros((1, PANJANG), dtype=np.float32)))
    kunci = next(k for k, v in uji.items() if len(tuple(v.shape)) == 2 and tuple(v.shape)[-1] == 1536)
    print("tensor embedding:", kunci)

    def tebak(X):
        if not len(X):
            return np.zeros((0, len(label_map)), dtype=np.float32)
        return model.forward((X - mean) / std)

    kelas_target = [c for c, nama in inv_map.items() if not nama.startswith("_")]
    semua = {}

    # 1. Uji bersih dari embedding yang sudah dihitung.
    emb = np.load(ML_DIR / "embeddings_perch" / "embeddings.npy")
    label = np.load(ML_DIR / "embeddings_perch" / "labels.npy")
    ids = json.loads((ML_DIR / "embeddings_perch" / "clip_ids.json").read_text())
    splits = json.loads((DATA / "splits_v2.json").read_text())
    posisi = {c: i for i, c in enumerate(ids)}
    idx = [posisi[c] for c in splits["test"] if c in posisi]
    semua["bersih"] = metrik(label[idx], tebak(emb[idx]), inv_map, thresholds, kelas_target)
    print("  bersih:", semua["bersih"])

    # 2. Korpus lapangan.
    field = DATA / "field"
    manifest = list(csv.DictReader(open(field / "manifest.csv", encoding="utf-8")))
    aud = field / "audio"

    for grup in ("inat", "xc_noisy", "other"):
        baris = [r for r in manifest if r["group"] == grup]
        peta_nama = {}
        berkas = []
        for r in baris:
            b = aud / r["local_path"].replace("field/audio/", "")
            if not b.exists():
                continue
            berkas.append(b)
            peta_nama[b.name] = r["species_scientific"]

        X, sumber = hitung_embedding(fn, kunci, berkas, args.maks_jendela)
        probs = tebak(X)
        entri = {"jumlah_berkas": len(berkas), "jumlah_jendela": int(len(X))}
        if grup == "other":
            entri["deteksi_palsu"] = deteksi_palsu(probs, inv_map, thresholds, kelas_target)
        else:
            # Label diambil per jendela memakai nama berkas asal, karena satu
            # berkas menghasilkan beberapa jendela dan jumlahnya tidak sama
            # antar berkas.
            y = np.array([label_map[peta_nama[n]] for n in sumber])
            entri.update(metrik(y, probs, inv_map, thresholds, kelas_target))
            entri["berkas_terbaca"] = len(berkas)
        semua[grup] = entri
        print(f"  {grup}:", entri)

    out = REPORTS / f"field_metrics{args.akhiran}.json"
    out.write_text(json.dumps(semua, indent=2, ensure_ascii=False))
    print("\nlaporan:", out.relative_to(REPO))
    return 0


if __name__ == "__main__":
    sys.exit(main())
