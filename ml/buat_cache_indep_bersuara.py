"""Ubah embedding jendela bersuara menjadi cache per klip untuk G2-4 (K3).

`ml/uji_independen.py` membaca cache embedding sebagai SATU berkas .npy per
klip dengan bentuk (n_jendela, 1024). `ml/extract_jendela_bersuara.py` justru
menulis satu embeddings.npy gabungan plus clip_ids.json berakhiran `__w<N>`.
Skrip ini menjembatani keduanya supaya kandidat K3 dinilai lewat jalur ukur
yang sama persis dengan baseline, bukan lewat skrip tandingan.

Pembatasan pool yang WAJIB: cache baseline berisi 131 klip dengan sha256
daftar id tertentu, sedangkan ekstraksi K3 menghasilkan 135 klip (3 klip dulu
gagal dibaca, 1 lainnya tidak masuk cache lama). Kalau kandidat dinilai pada
135 klip sementara baseline pada 131, angkanya tidak sebanding dan G2-4 tidak
sah. Karena itu keluaran dibatasi ke id yang ADA di cache baseline, dan
sha256-nya dicetak untuk dibandingkan.

Jalankan:
  source .venv/bin/activate && python ml/buat_cache_indep_bersuara.py
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
ML = ROOT / "ml"
POLA = re.compile(r"__w\d+$")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--emb-jendela", default=str(ML / "embeddings_bersuara_indep"))
    ap.add_argument("--cache-baseline",
                    default=str(ML / "data" / "uji_independen" / "embedding_cache"))
    ap.add_argument("--out-dir",
                    default=str(ML / "data" / "uji_independen" / "cache_bersuara"))
    a = ap.parse_args()

    src = Path(a.emb_jendela)
    base = Path(a.cache_baseline)
    out = Path(a.out_dir)

    emb = np.load(src / "embeddings.npy")
    ids = json.loads((src / "clip_ids.json").read_text())
    print(f"jendela: {len(ids)}, dim: {emb.shape[1]}")

    per_klip: dict[str, list[int]] = collections.defaultdict(list)
    for i, cid in enumerate(ids):
        per_klip[POLA.sub("", cid)].append(i)
    print(f"klip hasil ekstraksi K3: {len(per_klip)}")

    id_baseline = {p.stem for p in base.glob("*.npy")}
    print(f"klip di cache baseline : {len(id_baseline)}")

    dipakai = sorted(set(per_klip).intersection(id_baseline))
    lewat = sorted(set(per_klip).difference(id_baseline))
    kurang = sorted(id_baseline.difference(per_klip))
    print(f"\ndipakai (irisan)       : {len(dipakai)}")
    if lewat:
        print(f"dilewati, tidak ada di baseline: {len(lewat)} {lewat[:3]}")
    if kurang:
        print(f"ADA di baseline tapi tidak terekstrak: {len(kurang)} {kurang[:3]}")
        print("  G2-4 tidak sebanding kalau daftar ini tidak kosong.")

    out.mkdir(parents=True, exist_ok=True)
    for cid in dipakai:
        rows = per_klip[cid]
        blok = np.asarray(emb[rows], dtype=np.float32)
        np.save(out / f"{cid}.npy", blok)

    sha_baru = hashlib.sha256("\n".join(dipakai).encode("utf-8")).hexdigest()
    sha_base = hashlib.sha256(
        "\n".join(sorted(id_baseline)).encode("utf-8")).hexdigest()
    print(f"\nsha256 pool kandidat : {sha_baru}")
    print(f"sha256 pool baseline : {sha_base}")
    print("POOL SEBANDING" if sha_baru == sha_base else
          "POOL BEDA -> sebutkan ini saat melaporkan G2-4")
    print(f"\nOutput: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
