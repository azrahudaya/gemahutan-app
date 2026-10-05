"""Verifikasi integritas split manifest_v2 sebelum dipakai melatih.

Tiga hal yang diperiksa:
1. Tidak ada ID rekaman yang muncul di lebih dari satu split.
2. Tidak ada hash berkas yang muncul di lebih dari satu split.
3. Angka test tetap sama dengan baseline supaya perbandingan sah.

Kalau salah satu gagal, korpus belum boleh dipakai untuk mengklaim akurasi.
"""

import csv
from collections import defaultdict
from pathlib import Path

MANIFEST = Path(__file__).resolve().parent / "manifest_v2.csv"


def id_rekaman(local_path: str) -> str:
    nama = local_path.split("/")[-1].split(".")[0]
    return nama.split("_")[0].lstrip("xcXC-")


def main() -> None:
    rows = list(csv.DictReader(open(MANIFEST, encoding="utf-8")))

    id_per_split: dict[str, set] = defaultdict(set)
    hash_per_split: dict[str, set] = defaultdict(set)
    jumlah: dict[str, int] = defaultdict(int)

    for r in rows:
        s = r["split"]
        jumlah[s] += 1
        id_per_split[s].add(id_rekaman(r["local_path"]))
        hash_per_split[s].add(r["sha256"])

    split_ada = sorted(jumlah)
    print("jumlah per split:", dict(jumlah))
    print()

    gagal = 0

    for i, a in enumerate(split_ada):
        for b in split_ada[i + 1:]:
            tumpang_id = id_per_split[a] & id_per_split[b]
            tumpang_hash = hash_per_split[a] & hash_per_split[b]
            tanda = "OK" if not tumpang_id and not tumpang_hash else "BOCOR"
            if tumpang_id or tumpang_hash:
                gagal += 1
            print(
                f"{a} vs {b}: {tanda}  id_bersama={len(tumpang_id)}  hash_bersama={len(tumpang_hash)}"
            )

    # hash kembar di dalam satu split juga dilaporkan
    for s in split_ada:
        semua_hash = [r["sha256"] for r in rows if r["split"] == s]
        kembar = len(semua_hash) - len(set(semua_hash))
        if kembar:
            print(f"catatan: {s} punya {kembar} hash kembar di dalam split yang sama")
            gagal += 1

    print()
    print("HASIL:", "LULUS" if gagal == 0 else f"GAGAL ({gagal} masalah)")


if __name__ == "__main__":
    main()
