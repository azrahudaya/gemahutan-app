"""Buat splits_v4.json: buang klip lisensi terlarang dari latih/val.

Membaca manifest_latih_produksi.csv (lisensi per klip dari T3) dan membuang
klip dengan lisensi ND / all rights reserved / lihat-berkas-asli / tidak
diketahui. Uji (test) tidak diubah.

Jalankan: .venv/bin/python ml/buat_splits_lisensi.py
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "ml/data"

LISENSI_TERLARANG = ("nd", "lihat-berkas-asli", "all rights reserved",
                     "unknown", "tidak diketahui", "")


def terlarang(lis: str) -> bool:
    teks = (lis or "").strip().lower()
    return teks in LISENSI_TERLARANG or "-nd" in teks or "/nd" in teks


def main() -> int:
    manifest = DATA / "manifest_latih_produksi.csv"
    lis = {r["clip_id"]: (r.get("license") or "").strip().lower()
           for r in csv.DictReader(manifest.open())}

    sp = json.loads((DATA / "splits_v3.json").read_text())

    def buang(ids):
        dibuang = [c for c in ids if c in lis and terlarang(lis[c])]
        return [c for c in ids if c not in set(dibuang)], dibuang

    train_baru, buang_tr = buang(sp["train"])
    val_baru, buang_val = buang(sp["val"])

    out = {
        "train": train_baru,
        "val": val_baru,
        "test": sp["test"],
    }
    (DATA / "splits_v4.json").write_text(json.dumps(out, indent=2))

    print(f"latih: {len(sp['train'])} -> {len(train_baru)} (dibuang {len(buang_tr)})")
    print(f"val  : {len(sp['val'])} -> {len(val_baru)} (dibuang {len(buang_val)})")
    print(f"uji  : {len(sp['test'])} (tetap)")
    print("tersimpan: ml/data/splits_v4.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
