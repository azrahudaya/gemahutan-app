"""Subset kecil dari tangga degradasi, koheren dengan splits test ND-free.

Hasil di ml/data/degraded_subset/<tingkat>/<clip_id>.wav, dipotong ke 3 detik.
Sampling acak 96 klip dari test set (127) untuk konsistensi ruang dan waktu.
"""
import sys
from pathlib import Path as P

import degradation as dg  # type: ignore

ML = P(__file__).resolve().parent
SUB = ML / "data" / "degraded_subset"
SUB.mkdir(parents=True, exist_ok=True)

# 3 tingkat representatif: bersih kontrol, hujan ringan (medium), jarak 30m (medium)
TINGKAT = ["kontrol_reencode", "hujan_ringan", "jarak_30m"]
SAMPEL = 96  # <= 127 dengan seed tetap
BATAS_DETIK = 3.0

# Ganti OUT_DIR modul ke subset folder
dg.SPLITS = ML / "data" / "splits.json"
dg.MANIFEST = ML / "data" / "manifest.csv"
dg.OUT_DIR = SUB
dg.PARAMS = SUB / "params.json"


def main():
    sys.argv = [
        "degradation.py",
        "--tiers", ",".join(TINGKAT),
        "--sampel", str(SAMPEL),
        "--batas-detik", str(BATAS_DETIK),
        "--ganti",
    ]
    rc = dg.main()
    print(f"Output di {SUB.relative_to(ML.parent)}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
