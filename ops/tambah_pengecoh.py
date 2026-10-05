"""Tambah klip pengecoh ke korpus lapangan tanpa menimpa korpus yang ada.

Latar: deteksi palsu sekarang diukur hanya pada 21 berkas pengecoh dari satu
sumber (Xeno-canto), jadi satu berkas menggeser hasil sekitar 0,8 poin. Angka
itu terlalu bergoyang untuk dipakai mengklaim perbaikan.

Kenapa tidak menjalankan ml/data/field_corpus.py lagi: main() di skrip itu
membangun ulang manifest dari nol, jadi korpus lapangan yang sekarang akan
tertimpa. Skrip ini hanya MENAMBAH.

Syarat yang ditegakkan:
1. Lisensi ND dibuang, karena pipeline memotong klip (karya turunan).
2. Klip yang clip_id-nya sudah ada di manifest lapangan dilewati.
3. Klip yang sudah dipakai latih di manifest v2 DIBUANG. Tanpa saringan ini,
   pengecoh akan bocor ke data latih dan angka deteksi palsu jadi tidak sah.
"""
import csv
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "ml" / "data"))

import field_corpus as fc  # noqa: E402

# Spesies Indonesia di luar 25 target. Dipilih yang cukup sering terekam dan
# beberapa di antaranya sekeluarga dengan target, jadi pengecohnya benar-benar
# menantang, bukan burung yang suaranya jelas berbeda.
SPESIES_PENGECOH_TAMBAHAN = [
    "Acridotheres javanicus",
    "Collocalia linchi",
    "Alcedo meninting",
    "Aethopyga mystacalis",
    "Centropus sinensis",
    "Corvus enca",
    "Orthotomus ruficeps",
    "Dicaeum trochileum",
    "Turnix suscitator",
    "Zosterops palpebrosus",
    "Halcyon cyanoventris",
    "Megalaima javensis",
    "Megalaima armillaris",
    "Pellorneum rostratum",
    "Pericrocotus cinnamomeus",
    "Streptopelia bitorquata",
    "Treron griseicauda",
    "Oriolus chinensis",
    "Merops leschenaulti",
    "Merops viridis",
    "Lonchura maja",
    "Lonchura leucogastroides",
    "Nisaetus bartelsi",
    "Ketupa ketupu",
    "Dendrocygna arcuata",
    "Accipiter badius",
    "Hemipus hirundinaceus",
    "Aethopyga siparaja",
]

PER_SPESIES = 6


def main() -> int:
    fc._muat_env()
    if not fc.XC_API_KEY:
        print("XC_API_KEY tidak ada, tidak bisa panen")
        return 1

    if not fc.MANIFEST.exists():
        print(f"manifest lapangan tidak ada: {fc.MANIFEST}")
        return 1

    with fc.MANIFEST.open() as fh:
        baris_lama = list(csv.DictReader(fh))
    print(f"manifest lapangan sekarang: {len(baris_lama)} baris")

    # Klip yang sudah dipakai latih di korpus v2 harus dibuang dari pengecoh.
    v2 = ROOT / "ml" / "data" / "manifest_v2.csv"
    id_latih: set[str] = set()
    if v2.exists():
        with v2.open() as fh:
            id_latih = {r["clip_id"] for r in csv.DictReader(fh)}
        print(f"klip di korpus v2 (harus dihindari): {len(id_latih)}")

    skip_ids = {r["clip_id"] for r in baris_lama} | id_latih
    cache = json.loads(fc.CACHE.read_text()) if fc.CACHE.exists() else {}

    baris_baru: list[dict] = []
    print(f"panen pengecoh: {len(SPESIES_PENGECOH_TAMBAHAN)} spesies, maks {PER_SPESIES} per spesies")
    fc.panen_xc_spesies(SPESIES_PENGECOH_TAMBAHAN, PER_SPESIES, "other", cache, skip_ids, baris_baru)

    # Saringan terakhir: buang apa pun yang ternyata sudah ada di korpus v2.
    sebelum = len(baris_baru)
    baris_baru = [b for b in baris_baru if b["clip_id"] not in id_latih]
    if sebelum != len(baris_baru):
        print(f"  dibuang karena bocor ke latih: {sebelum - len(baris_baru)}")

    if not baris_baru:
        print("tidak ada pengecoh baru")
        return 0

    # Cadangkan manifest sebelum ditulis.
    cadangan = fc.MANIFEST.with_suffix(".csv.bak-sebelum-tambah-pengecoh")
    shutil.copy(fc.MANIFEST, cadangan)
    print(f"cadangan: {cadangan}")

    semua = baris_lama + baris_baru
    with fc.MANIFEST.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(baris_lama[0].keys()))
        writer.writeheader()
        writer.writerows(semua)

    fc.CACHE.write_text(json.dumps(cache))

    per_group: dict[str, int] = {}
    for b in semua:
        per_group[b["group"]] = per_group.get(b["group"], 0) + 1
    print()
    print("ringkasan korpus lapangan setelah ditambah:")
    for k, v in sorted(per_group.items()):
        print(f"  {k}: {v} berkas")
    print(f"  total: {len(semua)} berkas (sebelumnya {len(baris_lama)}, bertambah {len(baris_baru)})")

    # Cek lisensi ND tidak lolos.
    nd = [b["clip_id"] for b in semua if fc.lisensi_ditolak(b.get("license", ""))]
    print(f"  klip berlisensi ND di manifest: {len(nd)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
