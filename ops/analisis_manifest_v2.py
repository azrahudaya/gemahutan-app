"""Periksa manifest_v2: berapa rekaman unik di balik tiap spesies.

Klip dari SEA-Bird dan ULM bisa berasal dari satu rekaman Xeno-canto yang sama
tetapi dipotong menjadi banyak segmen. Kalau begitu, jumlah klip tidak sama
dengan jumlah rekaman, dan keragaman data sebenarnya lebih kecil dari yang
terlihat. Skrip ini mengukur rasionya supaya angka itu tidak disalahartikan.
"""

import csv
from collections import Counter, defaultdict
from pathlib import Path

MANIFEST = Path(__file__).resolve().parent / "manifest_v2.csv"


def id_rekaman(local_path: str) -> str:
    """Ambil ID rekaman dari nama berkas: xc<angka>_<ms>.wav atau <angka>.mp3."""
    nama = local_path.split("/")[-1].split(".")[0]
    return nama.split("_")[0].lstrip("xcXC-")


def main() -> None:
    rows = list(csv.DictReader(open(MANIFEST, encoding="utf-8")))
    klip: Counter = Counter()
    rekaman: dict[str, set] = defaultdict(set)

    for r in rows:
        sp = r["species_scientific"]
        klip[sp] += 1
        rekaman[sp].add(id_rekaman(r["local_path"]))

    print(f"{'spesies':34s} {'klip':>6s} {'rekaman':>8s} {'klip/rekaman':>13s}")
    print("-" * 66)
    for sp in sorted(klip, key=lambda x: -klip[x]):
        n_rek = len(rekaman[sp])
        print(f"{sp:34s} {klip[sp]:6d} {n_rek:8d} {klip[sp] / max(n_rek, 1):13.1f}")

    total_klip = sum(klip.values())
    total_rek = len(set().union(*rekaman.values()))
    print("-" * 66)
    print(f"{'TOTAL':34s} {total_klip:6d} {total_rek:8d} {total_klip / max(total_rek, 1):13.1f}")


if __name__ == "__main__":
    main()
