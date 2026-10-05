"""Salin ambang hasil kalibrasi ke kolom species.default_threshold.

Halaman Spesies menampilkan kolom default_threshold dari database, sedangkan
pipeline memakai ml/reports/thresholds.json. Keduanya sempat berbeda di 23 dari
25 spesies, jadi angka yang dibaca pengguna bukan angka yang benar-benar dipakai
untuk memutuskan sebuah deteksi.

Pakai:
    python3 ops/sync_thresholds.py            # tulis perubahan
    python3 ops/sync_thresholds.py --periksa  # hanya laporkan selisih
"""
import argparse
import subprocess
import sys
from pathlib import Path

from ml.ambang import muat_ambang

ROOT = Path(__file__).resolve().parent.parent
THRESHOLDS = ROOT / "ml" / "reports" / "thresholds.json"


def jalankan_sql(sql: str) -> str:
    hasil = subprocess.run(
        ["docker", "compose", "exec", "-T", "db", "psql", "-U", "gemahutan",
         "-d", "gemahutan", "-Atc", sql],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if hasil.returncode != 0:
        print(hasil.stderr.strip()[:400], file=sys.stderr)
        raise SystemExit(1)
    return hasil.stdout


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--periksa", action="store_true", help="hanya laporkan selisih")
    args = parser.parse_args()

    if not THRESHOLDS.exists():
        print(f"tidak ada {THRESHOLDS}")
        return 1

    ambang = muat_ambang(THRESHOLDS)
    baris = [b for b in jalankan_sql(
        "select scientific_name, default_threshold from species"
    ).splitlines() if "|" in b]
    db = {nama: float(nilai) for nama, nilai in (b.split("|") for b in baris)}

    perlu = []
    for spesies, nilai in sorted(ambang.items()):
        if spesies == "_negative":
            continue
        sekarang = db.get(spesies)
        if sekarang is None:
            print(f"  {spesies}: belum ada di database, dilewati")
            continue
        if abs(sekarang - float(nilai)) > 1e-9:
            perlu.append((spesies, sekarang, float(nilai)))

    print(f"selisih ambang: {len(perlu)} dari {len([k for k in ambang if k != '_negative'])} spesies")
    for spesies, lama, baru in perlu[:10]:
        print(f"  {spesies:<28} {lama} -> {baru}")

    if args.periksa:
        return 0

    for spesies, _, baru in perlu:
        jalankan_sql(
            f"update species set default_threshold = {baru} "
            f"where scientific_name = '{spesies}'"
        )
    print(f"{len(perlu)} baris diperbarui lewat psql di container db")

    sisa = 0
    db2 = {
        nama: float(nilai)
        for nama, nilai in (
            b.split("|") for b in jalankan_sql(
                "select scientific_name, default_threshold from species"
            ).splitlines() if "|" in b
        )
    }
    for spesies, nilai in ambang.items():
        if spesies == "_negative" or spesies not in db2:
            continue
        if abs(db2[spesies] - float(nilai)) > 1e-9:
            sisa += 1
    print(f"verifikasi: {sisa} spesies masih berbeda")
    return 0 if sisa == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
