"""Buat berkas split kontrol yang hanya memuat klip lama dari korpus v2.

Tujuan: memisahkan dua kemungkinan penyebab turunnya akurasi uji v2 (0,6535 dari
0,6772). Kalau pelatihan dengan split kontrol ini mengembalikan angka sekitar
0,6772, berarti skripnya benar dan penyebabnya memang data eksternal. Kalau
angkanya juga turun, berarti ada yang berubah di skrip atau embedding.

Pemakaian:
    python3 ops/buat_split_kontrol.py
"""

import csv
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
MANIFEST = BASE / "ml" / "data" / "manifest_v2.csv"
SPLITS = BASE / "ml" / "data" / "splits_v2.json"
OUT = BASE / "ml" / "data" / "splits_v2_kontrol.json"


def main() -> None:
    rows = list(csv.DictReader(open(MANIFEST, encoding="utf-8")))
    splits = json.load(open(SPLITS, encoding="utf-8"))

    lama = {r["clip_id"] for r in rows if r["source"] == "xeno-canto"}
    print("klip lama (xeno-canto) :", len(lama))

    baru = {}
    for nama in ("train", "val", "test"):
        daftar = [c for c in splits[nama] if c in lama]
        baru[nama] = daftar
        print(f"  {nama:6s} {len(daftar)} dari {len(splits[nama])}")

    baru["stats"] = {
        "catatan": "Split kontrol: hanya klip xeno-canto lama, tanpa data eksternal.",
        "total": sum(len(baru[k]) for k in ("train", "val", "test")),
    }
    OUT.write_text(json.dumps(baru, indent=2, ensure_ascii=False), encoding="utf-8")
    print("ditulis:", OUT.relative_to(BASE))


if __name__ == "__main__":
    main()
