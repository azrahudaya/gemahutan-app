"""Tambah rekaman ponsel iNaturalist ke set uji independen.

Alasan: set uji independen dari Xeno-canto hanya 51 klip karena kuota kualitas
C/D/E untuk spesies target hampir habis. Selang kepercayaannya jadi lebar (0,49
sampai 0,75). Rekaman ponsel iNaturalist menambah volume DAN lebih mirip kondisi
lapangan daripada rekaman Xeno-canto berkualitas bagus.

Syarat yang sama tetap ditegakkan: clip_id yang sudah ada di manifest mana pun
dilewati, lisensi ND dibuang, dan hasilnya tidak masuk data latih.
"""
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "ml" / "data"))

import field_corpus as fc  # noqa: E402

TUJUAN = ROOT / "ml" / "data" / "uji_independen"
MANIFEST = TUJUAN / "manifest.csv"
PER_SPESIES = 6


def main() -> int:
    fc._muat_env()

    label_map = json.loads((ROOT / "ml/embeddings_v2/label_map.json").read_text())
    target = sorted(k for k in label_map if not k.startswith("_"))

    terpakai: set[str] = set()
    for f in (
        ROOT / "ml/data/manifest_v2.csv",
        ROOT / "ml/data/field/manifest.csv",
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
    print(f"set uji independen sekarang: {len(baris_lama)} klip")
    if not baris_lama:
        print("manifest set independen belum ada, jalankan ops/panen_uji_independen.py dulu")
        return 1

    # panen_inat menambahkan clip_id baru KE DALAM skip_ids, jadi himpunan itu
    # harus disalin dulu. Kalau tidak, saringan di bawah akan membuang semua
    # rekaman yang baru saja diunduh.
    sebelum = set(terpakai)

    baris_baru: list[dict] = []
    asli_audio, asli_data = fc.AUDIO_DIR, fc.DATA_DIR
    fc.AUDIO_DIR = TUJUAN / "audio"
    fc.DATA_DIR = TUJUAN
    try:
        print(f"panen iNaturalist, maks {PER_SPESIES} per spesies")
        fc.panen_inat(target, PER_SPESIES, terpakai, baris_baru)
    finally:
        fc.AUDIO_DIR, fc.DATA_DIR = asli_audio, asli_data

    unik: dict[str, dict] = {}
    for b in baris_baru:
        unik.setdefault(b["clip_id"], b)
    baris_baru = [b for b in unik.values() if b["clip_id"] not in sebelum]
    if not baris_baru:
        print("tidak ada rekaman iNaturalist baru")
        return 0

    semua = baris_lama + baris_baru
    with MANIFEST.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(baris_lama[0].keys()))
        writer.writeheader()
        writer.writerows(semua)

    nd = [b["clip_id"] for b in semua if fc.lisensi_ditolak(b.get("license", ""))]
    per_kelas: dict[str, int] = {}
    for b in semua:
        per_kelas[b["species_scientific"]] = per_kelas.get(b["species_scientific"], 0) + 1
    print()
    print(f"set uji independen: {len(semua)} klip (bertambah {len(baris_baru)})")
    print(f"  berlisensi ND: {len(nd)}")
    print(f"  spesies terwakili: {len(per_kelas)} dari {len(target)}")
    print(f"  sumber: {sorted({b.get('source') for b in semua})}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
