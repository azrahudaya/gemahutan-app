"""Cetak struktur local_path pada manifest_v2 supaya folder sumber bisa disalin tepat."""

import csv
from collections import Counter
from pathlib import Path

MANIFEST = Path("/opt/kerja/ml/data/manifest_v2.csv")


def main() -> None:
    rows = list(csv.DictReader(open(MANIFEST, encoding="utf-8")))

    dua = Counter("/".join(r["local_path"].split("/")[:2]) for r in rows)
    print("struktur dua tingkat teratas:")
    for k, v in sorted(dua.items()):
        print(f"  {v:6d}  {k}")

    print()
    print("contoh satu baris per sumber:")
    terlihat = set()
    for r in rows:
        s = r["source"]
        if s in terlihat:
            continue
        terlihat.add(s)
        print(f"  {s:22s} {r['local_path']}")


if __name__ == "__main__":
    main()
