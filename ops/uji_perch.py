"""Uji apakah model Perch bisa dimuat dan menghasilkan embedding.

Perch 2.0 didistribusikan sebagai TensorFlow SavedModel. Dokumentasinya menyebut
versi ini butuh TensorFlow 2.20 dan GPU, tetapi itu belum tentu syarat keras.
Skrip ini menguji apa adanya: kalau berhasil dimuat di CPU, embedding bisa
dihitung di mesin lokal tanpa Colab. Kalau gagal, jalur Colab yang dipakai.

Jalankan dari root repo:
    .venv/bin/python3 ops/uji_perch.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

MODEL_DIR = Path(__file__).resolve().parent.parent / "ml" / "models_perch"
SR = 32000
DURASI_S = 5.0


def main() -> int:
    if not (MODEL_DIR / "saved_model.pb").exists():
        print("SavedModel tidak ada di", MODEL_DIR)
        return 1

    import tensorflow as tf

    print("TensorFlow  :", tf.__version__)
    print("GPU terdeteksi:", len(tf.config.list_physical_devices("GPU")))
    print("SavedModel  :", MODEL_DIR)

    try:
        model = tf.saved_model.load(str(MODEL_DIR))
    except Exception as exc:
        print("GAGAL memuat SavedModel:", repr(exc)[:400])
        return 2

    print("Berhasil dimuat. Signature yang tersedia:")
    sigs = list(getattr(model, "signatures", {}).keys())
    print("  signatures:", sigs[:10])
    print("  atribut   :", [a for a in dir(model) if not a.startswith("_")][:20])

    # Coba panggil signature utama dengan audio senyap 5 detik pada 32 kHz.
    audio = np.zeros(int(SR * DURASI_S), dtype=np.float32)
    for nama in sigs:
        fn = model.signatures[nama]
        print(f"\nMencoba signature '{nama}'")
        print("  input :", {k: (v.shape, v.dtype.name) for k, v in fn.structured_input_signature[1].items()})
        try:
            keluaran = fn(tf.constant(audio))
            print("  output:")
            for k, v in keluaran.items():
                bentuk = tuple(v.shape)
                print(f"    {k}: {bentuk} {v.dtype.name}")
        except Exception as exc:
            print("  gagal dipanggil:", repr(exc)[:300])

    return 0


if __name__ == "__main__":
    sys.exit(main())
