"""Panen set uji INDEPENDEN dari Xeno-canto untuk 25 spesies target.

Kenapa: split uji lama 127 klip itu wakil yang jujur (100 persen Xeno-canto)
tetapi presisinya rendah, satu klip menggeser 0,8 poin. Memperbesar split dengan
membagi ulang korpus gagal karena korpus didominasi sumber luar yang lebih mudah
(lihat ml/akurasi_per_sumber.py). Jadi cara yang benar adalah memanen klip
Xeno-canto BARU untuk spesies target.

Klip hasil panen ini sengaja TIDAK dimasukkan ke data latih. Fungsinya hanya
sebagai set uji independen, jadi:
- tidak perlu latih ulang model,
- tidak ada risiko kebocoran data latih,
- model diuji pada rekaman yang benar-benar belum pernah dilihat.

Semua clip_id yang sudah ada di manifest v2 dan manifest lapangan dilewati,
supaya set ini benar-benar bersih.
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
AUDIO_DIR = TUJUAN / "audio"
MANIFEST = TUJUAN / "manifest.csv"
PER_SPESIES = 8


def main() -> int:
    fc._muat_env()
    if not fc.XC_API_KEY:
        print("XC_API_KEY tidak ada")
        return 1

    label_map = json.loads((ROOT / "ml/embeddings_v2/label_map.json").read_text())
    target = sorted(k for k in label_map if not k.startswith("_"))
    print(f"spesies target: {len(target)}")

    # Semua clip_id yang sudah dipakai di korpus mana pun harus dihindari.
    terpakai: set[str] = set()
    for f in (ROOT / "ml/data/manifest_v2.csv", ROOT / "ml/data/field/manifest.csv"):
        if f.exists():
            with f.open() as fh:
                terpakai |= {r["clip_id"] for r in csv.DictReader(fh)}
    print(f"clip_id yang harus dihindari: {len(terpakai)}")

    cache = json.loads(fc.CACHE.read_text()) if fc.CACHE.exists() else {}

    TUJUAN.mkdir(parents=True, exist_ok=True)
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)

    # fc.panen_xc_spesies menulis ke AUDIO_DIR/<group>/<spesies>, dan AUDIO_DIR
    # adalah konstanta modul, jadi diarahkan dulu ke folder tujuan.
    asli_audio, asli_data = fc.AUDIO_DIR, fc.DATA_DIR
    fc.AUDIO_DIR = AUDIO_DIR
    fc.DATA_DIR = TUJUAN
    baris: list[dict] = []
    try:
        print(f"panen Xeno-canto kualitas C/D/E, maks {PER_SPESIES} per spesies")
        fc.panen_xc_spesies(target, PER_SPESIES, "uji", cache, terpakai, baris)
    finally:
        fc.AUDIO_DIR, fc.DATA_DIR = asli_audio, asli_data

    # Saringan akhir: jangan sampai ada satu pun yang sudah terpakai.
    bocor = [b for b in baris if b["clip_id"] in terpakai]
    if bocor:
        print(f"  dibuang karena sudah terpakai: {len(bocor)}")
        baris = [b for b in baris if b["clip_id"] not in terpakai]

    if not baris:
        print("tidak ada klip baru")
        return 0

    with MANIFEST.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(baris[0].keys()))
        writer.writeheader()
        writer.writerows(baris)
    fc.CACHE.write_text(json.dumps(cache))

    nd = [b["clip_id"] for b in baris if fc.lisensi_ditolak(b.get("license", ""))]
    print()
    print(f"set uji independen: {len(baris)} klip")
    print(f"  berlisensi ND: {len(nd)}")
    print(f"  manifest: {MANIFEST.relative_to(ROOT)}")
    print(f"  audio   : {AUDIO_DIR.relative_to(ROOT)}")
    per_kelas: dict[str, int] = {}
    for b in baris:
        per_kelas[b["species_scientific"]] = per_kelas.get(b["species_scientific"], 0) + 1
    print(f"  spesies terwakili: {len(per_kelas)} dari {len(target)}")
    kurang = [s for s in target if s not in per_kelas]
    if kurang:
        print(f"  tanpa klip baru: {len(kurang)} spesies")
    return 0


if __name__ == "__main__":
    sys.exit(main())
