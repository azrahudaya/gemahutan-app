"""Bangun manifest untuk ekstraksi jendela bersuara (K3, ML_10).

Kenapa perlu berkas sendiri, bukan langsung memakai manifest_v2.csv:

1. `ml/extract_jendela_bersuara.py` bawaannya membaca `manifest_v2.csv` saja.
   Korpus produksi v3 adalah manifest_v2 PLUS 98 klip kelas langka. Jadi
   ekstraksi lama (`ml/embeddings_bersuara`, 30 September) kehilangan tepat
   100 klip latih, 98 di antaranya kelas langka. Melatih K3 dari embedding itu
   berarti kelas langka diam-diam hilang dari data latih.
2. Hasil ekstraksi lama juga memuat 126 klip UJI. Itu wajar karena ekstraksi
   tidak tahu soal split, tetapi berarti penyaringan per split WAJIB dilakukan
   saat melatih. Skrip latih harus memilih baris menurut splits, bukan memakai
   seluruh berkas embedding.

Keluaran: ml/data/manifest_bersuara_v3.csv dengan kolom clip_id,
species_scientific, local_path. Hanya klip yang berkas audionya benar-benar ada.

Jalankan: source .venv/bin/activate && python ml/buat_manifest_bersuara.py
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "ml" / "data"
SUMBER = ["manifest_v2.csv", "kelas_langka/manifest.csv"]
OUT = DATA / "manifest_bersuara_v3.csv"
SPLITS = DATA / "splits_v3_nd_bersih.json"
KOLOM = ["clip_id", "species_scientific", "local_path"]


def main() -> int:
    baris: list[dict[str, str]] = []
    sudah: set[str] = set()
    tanpa_path = 0

    for src in SUMBER:
        p = DATA / src
        if not p.exists():
            print(f"PERINGATAN: {p} tidak ada, dilewati")
            continue
        n = 0
        with open(p, newline="") as f:
            for r in csv.DictReader(f):
                cid = (r.get("clip_id") or "").strip()
                if not cid or cid in sudah:
                    continue
                lp = (r.get("local_path") or "").strip()
                if not lp:
                    tanpa_path += 1
                    continue
                sudah.add(cid)
                n += 1
                baris.append({
                    "clip_id": cid,
                    "species_scientific": r.get("species_scientific", ""),
                    "local_path": lp,
                })
        print(f"{src}: +{n} klip")

    # Buang baris yang berkas audionya tidak ada, supaya ekstraksi tidak
    # berhenti di tengah setelah berjalan lama.
    ada_fisik = [r for r in baris if (DATA / r["local_path"]).exists()]
    hilang = len(baris) - len(ada_fisik)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=KOLOM)
        w.writeheader()
        w.writerows(ada_fisik)

    print(f"\nTotal klip dengan audio: {len(ada_fisik)}")
    if hilang:
        print(f"Dibuang karena berkas audio tidak ada: {hilang}")
    if tanpa_path:
        print(f"Dibuang karena local_path kosong: {tanpa_path}")

    if SPLITS.exists():
        sp = json.loads(SPLITS.read_text())
        latih = set(sp.get("train", [])) | set(sp.get("val", []))
        uji = set(sp.get("test", []))
        punya = {r["clip_id"] for r in ada_fisik}
        kurang = latih - punya
        print(f"\nCakupan klip latih: {len(latih) - len(kurang)}/{len(latih)}")
        if kurang:
            print(f"  BELUM tercakup: {len(kurang)} (contoh {sorted(kurang)[:4]})")
        print(f"Klip uji yang ikut ter-ekstrak: {len(uji & punya)}")
        print("  Klip uji WAJIB disaring saat melatih, lewat splits.")

    print(f"\nOutput: {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
