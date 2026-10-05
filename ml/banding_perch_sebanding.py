"""Siapkan perbandingan SEBANDING antara embedding BirdNET v3 dan Perch (K6).

Kenapa perlu: CV Perch pertama memberi F1 0,8386 melawan baseline BirdNET
0,7288. Selisih +0,11 itu terlalu besar untuk dipercaya apa adanya, dan
keluarannya sendiri menunjukkan sebabnya: pool XC yang di-OOF 796 klip pada
Perch versus 894 pada BirdNET. Aturan repo ini sudah menyebutnya: selalu cek
komposisi himpunan uji sebelum mengutip angkanya, dan akurasi tidak bisa
dibandingkan antar model kalau sampelnya berbeda.

Skrip ini menulis `ml/data/splits_irisan_perch.json`, yaitu splits yang hanya
memuat klip yang punya embedding di KEDUA sisi. Dengan itu BirdNET dan Perch
bisa dinilai pada klip yang sama persis.

Jalankan: source .venv/bin/activate && python ml/banding_perch_sebanding.py
"""
from __future__ import annotations

import collections
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ML = ROOT / "ml"
DATA = ML / "data"
SPLITS_IN = DATA / "splits_v3_nd_bersih.json"
OUT = DATA / "splits_irisan_perch.json"


def muat_ids(emb_dir: Path) -> set[str]:
    f = emb_dir / "clip_ids.json"
    if not f.exists():
        return set()
    return set(json.loads(f.read_text()))


def main() -> int:
    perch = muat_ids(ML / "embeddings_perch")
    v3 = muat_ids(ML / "embeddings_v3")
    if not perch or not v3:
        print("ERROR: clip_ids.json tidak lengkap di salah satu folder embedding")
        return 1

    print(f"klip embeddings_v3    : {len(v3)}")
    print(f"klip embeddings_perch : {len(perch)}")

    hilang = v3.difference(perch)
    print(f"ada di v3 tapi tidak di perch: {len(hilang)}")
    if hilang:
        pref = collections.Counter(h.split("-")[0] for h in hilang)
        print(f"  per prefiks: {dict(pref)}")
        kl = DATA / "kelas_langka" / "manifest.csv"
        if kl.exists():
            with open(kl, newline="") as fh:
                langka = {r["clip_id"] for r in csv.DictReader(fh)}
            print(f"  di antaranya klip KELAS LANGKA: {len(hilang.intersection(langka))}")

    sp = json.loads(SPLITS_IN.read_text())
    iris = perch.intersection(v3)

    print()
    for nama in ("train", "val", "test"):
        s = set(sp.get(nama, []))
        print(f"{nama:5s}: v3 {len(s.intersection(v3)):5d}  "
              f"perch {len(s.intersection(perch)):5d}  "
              f"irisan {len(s.intersection(iris)):5d}")

    baru: dict[str, object] = {}
    for k, v in sp.items():
        baru[k] = [c for c in v if c in iris] if isinstance(v, list) else v
    baru["catatan"] = (
        "Irisan klip yang ada di embeddings_v3 DAN embeddings_perch. Dipakai "
        "supaya BirdNET dan Perch dinilai pada klip yang sama persis. Dibuang "
        f"{len(hilang)} klip yang tidak punya embedding Perch."
    )
    OUT.write_text(json.dumps(baru, indent=2, ensure_ascii=False))

    print(f"\nOutput: {OUT}")
    print("Jalankan CV kedua sisi dengan --splits berkas ini, baru angkanya "
          "boleh dibandingkan.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
