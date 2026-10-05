"""Bersihkan SEA-Bird: buang rekaman berlisensi ND, lalu tulis metadata bersih.

Dataset card SEA-Bird menyebut lisensi CC BY 4.0, tetapi metadata per rekaman
menunjukkan lisensi asli dari Xeno-canto. Terukur 374 dari 1074 rekaman pada
subset 16 kHz dan 373 dari 1037 pada subset 44 kHz berlisensi NoDerivatives.

Pipeline GemaHutan memotong audio menjadi jendela 3 detik, dan pemotongan itu
termasuk derivasi. Jadi rekaman ND harus dibuang sebelum klip dipakai, sama
seperti yang sudah dilakukan pada dataset Xeno-canto utama.

Jalankan di VPS: python3 /opt/staging/bersihkan_seabird.py
"""

import csv
from pathlib import Path

BASE = Path("/opt/staging/seabird_clean")
META = {
    "seabird16k": Path("/opt/staging/seabird/seabird16k_metadata.csv"),
    "seabird44k": Path("/opt/staging/seabird/seabird44k_metadata.csv"),
}


def is_nd(lic: str) -> bool:
    """True kalau lisensi melarang derivasi."""
    teks = (lic or "").lower()
    return (
        "noderivatives" in teks
        or "by-nc-nd" in teks
        or "nd/2.5" in teks
        or "nd/3.0" in teks
        or "nd/4.0" in teks
    )


def main() -> None:
    ringkas = {}
    for subset, meta_path in META.items():
        folder = BASE / subset
        if not folder.exists():
            print(subset, "tidak ada, dilewati")
            continue

        rows = list(csv.DictReader(open(meta_path, encoding="utf-8")))
        nd_ids = {
            str(r["xeno-canto_id"]).strip().lstrip("xcXC")
            for r in rows
            if is_nd(r.get("license", ""))
        }
        bersih = [r for r in rows if not is_nd(r.get("license", ""))]

        dibuang = 0
        for berkas in folder.rglob("*.wav"):
            # nama berkas berbentuk xc<id>_<milidetik>.wav
            id_rekaman = berkas.stem.split("_")[0].lstrip("xcXC")
            if id_rekaman in nd_ids:
                berkas.unlink()
                dibuang += 1

        out_meta = BASE / (subset + "_metadata_ndfree.csv")
        with open(out_meta, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(bersih)

        ringkas[subset] = {
            "baris_metadata": len(rows),
            "baris_nd_dibuang": len(rows) - len(bersih),
            "berkas_dibuang": dibuang,
            "berkas_tersisa": len(list(folder.rglob("*.wav"))),
        }

    for k, v in ringkas.items():
        print(k, v)

    print("total berkas ND-free:", sum(v["berkas_tersisa"] for v in ringkas.values()))


if __name__ == "__main__":
    main()
