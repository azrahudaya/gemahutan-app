"""Ekstrak embedding Perch per JENDELA untuk pool uji independen (K6, G2-4).

Kenapa perlu: `ml/reports/k6_perch/README.md` mencatat nol dari 135 klip uji
independen punya embedding Perch, jadi syarat ketiga C14 (F1 independen) dan
gerbang G2-4 tidak bisa dihitung untuk K6. Skrip ini menutup lubang itu.

Dua hal yang ditiru dari perbaikan K3, bukan ditebak:

1. Fallback ffmpeg. librosa/soundfile TIDAK bisa membaca m4a. Pada pool ini 34
   klip m4a plus 2 mpga, seluruhnya rekaman ponsel iNaturalist, yaitu subset
   tersulit. Tanpa fallback, 36 klip hilang dan angkanya optimistis palsu.
2. Keluaran per klip sebagai satu .npy bentuk (n_jendela, 1536), supaya
   `ml/uji_independen.py --cache-dir` bisa menilainya lewat jalur ukur yang
   sama persis dengan baseline.

Jendela: Perch menuntut masukan 5,0 detik pada 32 kHz, sedangkan BirdNET 3,0
detik. Panjang jendela TIDAK BISA disamakan tanpa mengubah model. Yang disamakan
adalah rasio tumpang tindih: stride = setengah panjang jendela, jadi 2,5 detik
untuk Perch melawan 1,5 detik untuk BirdNET 3 detik. Klip lebih pendek dari 5
detik dipadding nol, sama seperti `ml/data/extract_perch.py`.

Jalankan: .venv-perch/bin/python3 ml/ekstrak_perch_indep.py
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

REPO = Path(__file__).resolve().parent.parent
ML = REPO / "ml"
INDEP = ML / "data" / "uji_independen"

SR = 32000
DURASI = 5.0
PANJANG = int(SR * DURASI)


def muat_audio_32k(path: Path) -> np.ndarray:
    """Muat audio penuh mono 32 kHz, dengan jalur cadangan ffmpeg untuk m4a/mpga."""
    import librosa

    try:
        y, _ = librosa.load(str(path), sr=SR, mono=True)
        return y.astype(np.float32)
    except Exception:
        pass

    with tempfile.TemporaryDirectory() as tmp:
        wav = str(Path(tmp) / "konversi.wav")
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", str(path),
             "-ar", str(SR), "-ac", "1", wav],
            check=True, timeout=180, capture_output=True,
        )
        y, _ = librosa.load(wav, sr=SR, mono=True)
        return y.astype(np.float32)


def potong_jendela(y: np.ndarray, stride_s: float) -> list[np.ndarray]:
    """Bagi audio jadi jendela 5 detik dengan stride tertentu.

    Klip di bawah 5 detik menghasilkan satu jendela yang dipadding nol, sama
    seperti jalur ekstraksi latih.
    """
    if len(y) <= PANJANG:
        return [np.pad(y, (0, PANJANG - len(y)))]
    langkah = int(SR * stride_s)
    out = []
    s = 0
    while s + PANJANG <= len(y):
        out.append(y[s:s + PANJANG])
        s += langkah
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default=str(INDEP / "manifest.csv"))
    ap.add_argument("--model-dir", default=str(ML / "models_perch"))
    ap.add_argument("--out-dir", default=str(INDEP / "cache_perch"))
    ap.add_argument("--stride", type=float, default=2.5)
    ap.add_argument("--maks-jendela", type=int, default=40,
                    help="batas jendela per klip supaya klip panjang tidak mendominasi biaya")
    a = ap.parse_args()

    sys.path.insert(0, str(ML / "data"))
    import tensorflow as tf
    from extract_perch import temukan_kunci_embedding

    gpu = tf.config.list_physical_devices("GPU")
    print("GPU:", gpu or "TIDAK ADA (jalan di CPU, lebih lambat)")

    model = tf.saved_model.load(a.model_dir)
    fn = model.signatures["serving_default"]
    kunci = None

    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    baris = list(csv.DictReader(open(a.manifest, encoding="utf-8")))
    print(f"klip di manifest: {len(baris)}")

    ok, gagal, lewat_ffmpeg = [], [], []
    total_jendela = 0
    for i, r in enumerate(baris):
        cid = r["clip_id"].strip()
        path = INDEP / r["local_path"].strip() if not r["local_path"].startswith("/") else Path(r["local_path"])
        if not path.exists():
            alt = ML / "data" / r["local_path"].strip()
            path = alt if alt.exists() else path
        if not path.exists():
            gagal.append({"clip_id": cid, "error": f"audio tidak ada: {path}"})
            continue
        try:
            import librosa
            try:
                librosa.load(str(path), sr=SR, mono=True)
            except Exception:
                lewat_ffmpeg.append(cid)
            y = muat_audio_32k(path)
            jendela = potong_jendela(y, a.stride)[: a.maks_jendela]
            batch = np.stack(jendela).astype(np.float32)
            keluaran = fn(tf.constant(batch))
            if kunci is None:
                kunci = temukan_kunci_embedding(keluaran)
                print("tensor embedding:", kunci, tuple(keluaran[kunci].shape))
            emb = np.asarray(keluaran[kunci]).astype(np.float32)
            np.save(out / f"{cid}.npy", emb)
            ok.append(cid)
            total_jendela += emb.shape[0]
        except Exception as exc:  # noqa: BLE001
            gagal.append({"clip_id": cid, "error": repr(exc)[:200]})
        if (i + 1) % 25 == 0:
            print(f"  {i + 1}/{len(baris)}  ok={len(ok)} gagal={len(gagal)}")

    lap = {
        "n_manifest": len(baris),
        "n_ok": len(ok),
        "n_gagal": len(gagal),
        "gagal": gagal,
        "n_lewat_ffmpeg": len(lewat_ffmpeg),
        "total_jendela": total_jendela,
        "stride_s": a.stride,
        "durasi_jendela_s": DURASI,
        "maks_jendela": a.maks_jendela,
        "out_dir": str(out),
    }
    rep = ML / "reports" / "k6_perch" / "ekstraksi_indep.json"
    rep.parent.mkdir(parents=True, exist_ok=True)
    rep.write_text(json.dumps(lap, indent=2, ensure_ascii=False))
    print(json.dumps({k: v for k, v in lap.items() if k != "gagal"}, indent=2, ensure_ascii=False))
    if gagal:
        print(f"GAGAL {len(gagal)} klip, 3 pertama: {gagal[:3]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
