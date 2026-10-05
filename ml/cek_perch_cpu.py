"""Buktikan apakah Perch SavedModel bisa jalan di CPU sama sekali.

Kenapa dipisah jadi skrip sendiri: pengukuran sumber daya gagal dengan pesan
"The current platform CPU is not among the platforms required by the module:
[CUDA]". Itu klaim besar (artinya K6 tidak bisa dipakai di server CPU), jadi
harus diuji sendiri dengan beberapa jalur, bukan disimpulkan dari satu traceback.

Tiga jalur dicoba, masing-masing terpisah:
1. signature serving_default langsung di CPU.
2. jit_compile dimatikan lewat tf.config.optimizer.
3. soft device placement, yaitu izinkan TF memilih perangkat sendiri.

Jalankan: .venv-perch/bin/python3 ml/cek_perch_cpu.py
"""
from __future__ import annotations

import json
import os
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ML = REPO / "ml"
SR, DURASI = 32000, 5.0


def main() -> int:
    os.environ["CUDA_VISIBLE_DEVICES"] = ""
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

    import numpy as np
    import tensorflow as tf

    hasil = {"gpu_terlihat": bool(tf.config.list_physical_devices("GPU")), "jalur": []}
    audio = np.zeros((1, int(SR * DURASI)), dtype=np.float32)

    def coba(nama, fn):
        try:
            keluaran = fn()
            bentuk = {k: tuple(v.shape) for k, v in keluaran.items()}
            hasil["jalur"].append({"nama": nama, "status": "BERHASIL", "keluaran": str(bentuk)[:200]})
            print(f"{nama}: BERHASIL {bentuk}")
            return True
        except Exception as exc:  # noqa: BLE001
            pesan = str(exc).replace("\n", " ")[:300]
            hasil["jalur"].append({"nama": nama, "status": "GAGAL", "error": pesan})
            print(f"{nama}: GAGAL {pesan}")
            return False

    model = tf.saved_model.load(str(ML / "models_perch"))
    fn = model.signatures["serving_default"]

    coba("serving_default di CPU", lambda: fn(tf.constant(audio)))

    tf.config.optimizer.set_jit(False)
    coba("jit dimatikan", lambda: fn(tf.constant(audio)))

    tf.config.set_soft_device_placement(True)
    coba("soft device placement", lambda: fn(tf.constant(audio)))

    hasil["bisa_di_cpu"] = any(j["status"] == "BERHASIL" for j in hasil["jalur"])
    out = ML / "reports" / "k6_perch" / "cek_cpu.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(hasil, indent=2, ensure_ascii=False))
    print("\nBISA DI CPU:", hasil["bisa_di_cpu"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
