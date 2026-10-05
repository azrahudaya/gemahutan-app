"""Panen tambahan untuk kelas langka, masuk ke DATA LATIH.

Masalah: enam kelas punya klip paling sedikit, dan beberapa di antaranya recall
nol pada model yang dipakai. Dicrurus macrocercus 23 klip (17 latih), Gallus
gallus 10, Prinia familiaris 11. Dengan 10 sampai 17 klip latih, gradiennya
jarang menyentuh kelas itu.

Skrip ini menambah klip Xeno-canto untuk kelas-kelas tersebut lalu menyimpannya
di folder terpisah. Klip ini CALON data latih, bukan data uji, jadi:
- clip_id yang sudah ada di manifest mana pun dilewati, termasuk set uji
  independen, supaya set uji tetap bersih,
- lisensi ND dibuang.
"""
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "ml" / "data"))

import field_corpus as fc  # noqa: E402

TUJUAN = ROOT / "ml" / "data" / "kelas_langka"
MANIFEST = TUJUAN / "manifest.csv"
PER_SPESIES = 20

# Ambang dipilih dari hitungan nyata: kelas dengan kurang dari 30 klip.
KELAS_LANGKA = [
    "Gallus gallus",
    "Prinia familiaris",
    "Chalcophaps indica",
    "Arachnothera longirostra",
    "Dicrurus macrocercus",
    "Hirundo tahitica",
    "Rhipidura javanica",
    "Lonchura punctulata",
    "Merops philippinus",
    "Haliastur indus",
]


def main() -> int:
    fc._muat_env()
    if not fc.XC_API_KEY:
        print("XC_API_KEY tidak ada")
        return 1

    terpakai: set[str] = set()
    for f in (
        ROOT / "ml/data/manifest_v2.csv",
        ROOT / "ml/data/field/manifest.csv",
        ROOT / "ml/data/uji_independen/manifest.csv",
        MANIFEST,
    ):
        if f.exists():
            with f.open() as fh:
                terpakai |= {r["clip_id"] for r in csv.DictReader(fh)}
    print(f"clip_id yang harus dihindari: {len(terpakai)}")

    baris_lama: list[dict] = []
    if MANIFEST.exists():
        with MANIFEST.open() as fh:
            baris_lama = list(csv.DictReader(fh))
    print(f"kelas langka sekarang: {len(baris_lama)} klip")

    sebelum = set(terpakai)
    baris_baru: list[dict] = []
    TUJUAN.mkdir(parents=True, exist_ok=True)

    asli_audio, asli_data = fc.AUDIO_DIR, fc.DATA_DIR
    fc.AUDIO_DIR = TUJUAN / "audio"
    fc.DATA_DIR = TUJUAN
    try:
        cache = json.loads(fc.CACHE.read_text()) if fc.CACHE.exists() else {}
        print(f"panen Xeno-canto, maks {PER_SPESIES} per spesies")
        fc.panen_xc_spesies(KELAS_LANGKA, PER_SPESIES, "tambahan", cache, terpakai, baris_baru)
        fc.CACHE.write_text(json.dumps(cache))
    finally:
        fc.AUDIO_DIR, fc.DATA_DIR = asli_audio, asli_data

    unik: dict[str, dict] = {}
    for b in baris_baru:
        unik.setdefault(b["clip_id"], b)
    baris_baru = [b for b in unik.values() if b["clip_id"] not in sebelum]
    if not baris_baru:
        print("tidak ada klip baru")
        return 0

    semua = baris_lama + baris_baru
    with MANIFEST.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(baris_baru[0].keys()))
        writer.writeheader()
        writer.writerows(semua)

    nd = [b["clip_id"] for b in semua if fc.lisensi_ditolak(b.get("license", ""))]
    per_kelas: dict[str, int] = {}
    for b in semua:
        per_kelas[b["species_scientific"]] = per_kelas.get(b["species_scientific"], 0) + 1
    print()
    print(f"kelas langka: {len(semua)} klip (bertambah {len(baris_baru)})")
    print(f"  berlisensi ND: {len(nd)}")
    for k in KELAS_LANGKA:
        print(f"    {k:30s} {per_kelas.get(k, 0):3d} klip baru")
    return 0


if __name__ == "__main__":
    sys.exit(main())
