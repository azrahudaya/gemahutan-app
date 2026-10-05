"""Bangun manifest_latih_produksi.csv: lisensi tiap klip latih+val produksi.

Sumber lisensi:
  xeno-canto (v2)  -- manifest_v2.csv
  xeno-canto (langka) -- kelas_langka/manifest.csv
  sea-bird / ulm / inatsounds -- manifest_v2.csv

Klip inatsounds (iNat) dulu ditulis 'lihat-berkas-asli' karena lisensi aslinya
tidak ada di parquet HuggingFace. Itu sudah TERPECAHKAN: lisensi per klip
diambil dari ANOTASI RESMI iNatSounds 2024 lewat ml/lisensi_inat_resmi.py,
yang menghasilkan ml/data/manifest_lisensi_inat.csv. Berkas itu ditimpakan di
sini supaya kolom license memuat lisensi sebenarnya, bukan placeholder.

Hasil pencocokan: 3205 dari 3205 klip ketemu, 29 di antaranya ND.

Jalankan: python3 ml/buat_manifest_lisensi.py
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ML_DIR = ROOT / "ml"
SPLITS_FILE = ML_DIR / "data" / "splits_v3.json"
OUT = ML_DIR / "data" / "manifest_latih_produksi.csv"

SUMBER_LISENSI = {
    "xeno-canto": "xeno-canto",
    "kelas-langka": "xeno-canto",
    "sea-bird": "zenodo SEA-Bird",
    "ulm-ds-lab": "ULM-DS-Lab metadata",
    "inatsounds-aves": "inat_sounds (berkas asli iNaturalist)",
    "inatsounds-insecta": "inat_sounds (berkas asli iNaturalist)",
    "inatsounds-mammalia": "inat_sounds (berkas asli iNaturalist)",
}


def main() -> int:
    sp = json.loads(SPLITS_FILE.read_text())
    train_val = set(sp["train"]) | set(sp["val"])

    rows = {}
    # Sumber 1: manifest_v2.csv
    v2_path = ML_DIR / "data" / "manifest_v2.csv"
    if v2_path.exists():
        with open(v2_path, newline='') as f:
            for r in csv.DictReader(f):
                cid = r["clip_id"]
                if cid in train_val:
                    rows[cid] = {
                        "clip_id": cid,
                        "source": r.get("source", ""),
                        "license": (r.get("license") or "").strip(),
                        "license_url": r.get("source_url", ""),
                        "sumber_lisensi": SUMBER_LISENSI.get(r.get("source", ""), "unknown"),
                    }

    # Sumber 2: kelas_langka/manifest.csv (98 klip XC tambahan v3)
    langka_path = ML_DIR / "data" / "kelas_langka" / "manifest.csv"
    if langka_path.exists():
        with open(langka_path, newline='') as f:
            for r in csv.DictReader(f):
                cid = r["clip_id"]
                if cid in train_val and cid not in rows:
                    rows[cid] = {
                        "clip_id": cid,
                        "source": r.get("source", "xeno-canto"),
                        "license": (r.get("license") or "").strip(),
                        "license_url": r.get("source_url", ""),
                        "sumber_lisensi": "xeno-canto",
                    }

    # Sumber 3: lisensi iNat dari ANOTASI RESMI iNatSounds 2024.
    # Ini menimpa placeholder 'lihat-berkas-asli' dengan lisensi sebenarnya.
    # Dibuat oleh ml/lisensi_inat_resmi.py; kalau belum ada, baris iNat tetap
    # memakai placeholder dan C17 akan GAGAL -- itu memang perilaku yang benar,
    # karena tanpa bukti per klip kita tidak boleh mengaku lisensinya sah.
    lisensi_inat = ML_DIR / "data" / "manifest_lisensi_inat.csv"
    n_ditimpa = 0
    if lisensi_inat.exists():
        with open(lisensi_inat, newline='') as f:
            for r in csv.DictReader(f):
                cid = r["clip_id"]
                if cid not in rows or r.get("status") == "tidak_ketemu":
                    continue
                rows[cid]["license"] = r["license"]
                rows[cid]["license_url"] = r["license_url"]
                rows[cid]["sumber_lisensi"] = r["sumber_lisensi"]
                n_ditimpa += 1
        print(f"lisensi iNat dari anotasi resmi: {n_ditimpa} baris ditimpa")
    else:
        print(f"PERINGATAN: {lisensi_inat} tidak ada, baris iNat tetap placeholder")
        print("  jalankan dulu: python ml/lisensi_inat_resmi.py")

    # Tulis CSV
    missing = sorted(train_val - set(rows.keys()))
    with open(OUT, "w", newline='') as f:
        w = csv.DictWriter(f, fieldnames=["clip_id", "source", "license",
                                          "license_url", "sumber_lisensi"])
        w.writeheader()
        for cid in sorted(rows):
            w.writerow(rows[cid])

    # Ringkasan
    forbidden = {"nd", "lihat-berkas-asli", "all rights reserved", "unknown",
                 "tidak diketahui", ""}
    n_forbidden = sum(1 for r in rows.values()
                      if r["license"].strip().lower() in forbidden
                      or "-nd" in r["license"].lower()
                      or "/nd" in r["license"].lower())

    print(f"train+val: {len(train_val)}")
    print(f"tertulis: {len(rows)}")
    print(f"missing (tanpa lisensi): {len(missing)}")
    if missing:
        print(f"  sample: {missing[:5]}")
    print(f"lisensi terlarang: {n_forbidden}")
    print(f"Output: {OUT}")
    return 0 if not missing else 1


if __name__ == "__main__":
    sys.exit(main())