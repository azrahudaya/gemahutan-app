"""Gabungkan embedding per JENDELA menjadi satu embedding per KLIP (K3, ML_10).

Kenapa langkah ini wajib ada, dengan bukti angkanya:

`ml/extract_jendela_bersuara.py` menulis satu baris per jendela dengan id
berakhiran `__w<N>`, contoh `xc-474011__w0`. Sementara seluruh resep latih dan
evaluasi memetakan id splits LANGSUNG ke baris embedding:

    idx = {cid: i for i, cid in enumerate(ids)}        # latih_produksi.py:125
    tr  = [c for c in sp["train"] if c in idx]         # latih_produksi.py:128

Karena `xc-1076362` tidak sama dengan `xc-474011__w0`, hasilnya terukur:
klip latih yang terpilih 0 dari 8073. Jadi embedding jendela TIDAK bisa dipakai
apa adanya oleh latih_produksi.py maupun evaluasi_bersarang.py.

Dua jalan keluar, dan yang dipilih di sini adalah yang pertama:

1. Gabungkan jendela per klip jadi satu vektor (dipakai di sini). Resep latih
   tidak perlu diubah sama sekali, dan evaluasi tetap di tingkat KLIP sehingga
   angkanya sebanding dengan baseline.
2. Memperluas splits ke id jendela. Ditolak karena evaluasi lalu berpindah ke
   tingkat jendela, dan aturan repo ini melarang membandingkan angka dengan cara
   ukur berbeda ("semua jendela" selalu lebih rendah dari "per berkas"). Selain
   itu jumlah baris jadi tidak seimbang antar klip, dan jendela dari satu klip
   bisa tersebar ke lipatan berbeda.

Yang dikerjakan: rata-rata vektor seluruh jendela bersuara milik satu klip.
Itu memenuhi maksud C18 (label diambil dari bagian rekaman yang benar-benar
bersuara, bukan 3 detik pertama) tanpa mengubah satuan evaluasi.

Keluaran: folder embedding bergaya sama dengan ml/embeddings_v3 (embeddings.npy,
clip_ids.json, labels.npy, label_map.json) plus ml/reports/pemilihan_jendela.json
yang dibaca audit C18.

Jalankan:
  source .venv/bin/activate && python ml/agregasi_jendela.py \
      --emb-jendela ml/embeddings_bersuara_v3 \
      --out-dir ml/embeddings_bersuara_v3_klip
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
ML = ROOT / "ml"
POLA_JENDELA = re.compile(r"__w\d+$")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--emb-jendela", default=str(ML / "embeddings_bersuara_v3"),
                    help="folder embedding per jendela")
    ap.add_argument("--out-dir", default=str(ML / "embeddings_bersuara_v3_klip"),
                    help="folder keluaran embedding per klip")
    ap.add_argument("--cara", choices=["rata", "maks"], default="rata",
                    help="rata = rata-rata jendela, maks = jendela bernorma terbesar")
    ap.add_argument("--laporan-c18", default=str(ML / "reports" / "pemilihan_jendela.json"),
                    help="tulis laporan C18 ke sini; kosongkan untuk melewati")
    a = ap.parse_args()

    src = Path(a.emb_jendela)
    out = Path(a.out_dir)
    for n in ("embeddings.npy", "clip_ids.json", "labels.npy", "label_map.json"):
        if not (src / n).exists():
            print(f"ERROR: {src / n} tidak ada")
            return 1

    emb = np.load(src / "embeddings.npy", mmap_mode="r")
    ids = json.loads((src / "clip_ids.json").read_text())
    lab = np.load(src / "labels.npy")
    label_map = json.loads((src / "label_map.json").read_text())
    print(f"jendela: {len(ids)}, dim: {emb.shape[1]}")

    # Kelompokkan baris menurut id klip (buang akhiran __w<N>).
    per_klip: dict[str, list[int]] = collections.defaultdict(list)
    for i, cid in enumerate(ids):
        per_klip[POLA_JENDELA.sub("", cid)].append(i)
    print(f"klip unik: {len(per_klip)}")

    # Label tiap jendela harus sama untuk satu klip. Kalau tidak, ada kekacauan
    # di ekstraksi dan hasilnya tidak boleh dipakai diam-diam.
    bentrok = [c for c, rows in per_klip.items() if len({int(lab[r]) for r in rows}) > 1]
    if bentrok:
        print(f"ERROR: {len(bentrok)} klip punya label jendela bertentangan, contoh {bentrok[:3]}")
        return 1

    urut = sorted(per_klip)
    hasil = np.zeros((len(urut), emb.shape[1]), dtype=np.float32)
    label_klip = np.zeros(len(urut), dtype=lab.dtype)
    n_jendela = []

    for k, cid in enumerate(urut):
        rows = per_klip[cid]
        blok = np.asarray(emb[rows], dtype=np.float32)
        if a.cara == "rata":
            hasil[k] = blok.mean(axis=0)
        else:
            hasil[k] = blok[int(np.argmax(np.linalg.norm(blok, axis=1)))]
        label_klip[k] = lab[rows[0]]
        n_jendela.append(len(rows))

    out.mkdir(parents=True, exist_ok=True)
    np.save(out / "embeddings.npy", hasil)
    (out / "clip_ids.json").write_text(json.dumps(urut, ensure_ascii=False))
    np.save(out / "labels.npy", label_klip)
    (out / "label_map.json").write_text(json.dumps(label_map, indent=2, ensure_ascii=False))

    nj = np.array(n_jendela)
    print(f"\nkeluaran: {out}")
    print(f"  baris: {hasil.shape[0]}, dim: {hasil.shape[1]}")
    print(f"  jendela per klip: min {nj.min()} median {int(np.median(nj))} maks {nj.max()}")

    # Cakupan terhadap splits, supaya ketahuan sebelum melatih.
    for nama in ("splits_v3_nd_bersih.json", "splits_v3.json"):
        sp_path = ML / "data" / nama
        if not sp_path.exists():
            continue
        sp = json.loads(sp_path.read_text())
        punya = set(urut)
        latih = set(sp.get("train", [])) | set(sp.get("val", []))
        print(f"  cakupan {nama}: latih {len(latih & punya)}/{len(latih)}, "
              f"uji {len(set(sp.get('test', [])) & punya)}/{len(sp.get('test', []))}")
        break

    if a.laporan_c18:
        lap = Path(a.laporan_c18)
        lap.parent.mkdir(parents=True, exist_ok=True)
        lap.write_text(json.dumps({
            "metode": "jendela_bersuara_rata" if a.cara == "rata" else "jendela_bersuara_maks",
            "emb_dir": str(out.resolve().relative_to(ROOT)),
            "emb_jendela": str(src.resolve().relative_to(ROOT)),
            "n_klip": int(hasil.shape[0]),
            "n_jendela_total": int(len(ids)),
            "jendela_per_klip_median": int(np.median(nj)),
            "stride": 1.5,
            "segmen": 3.0,
            "energi_min_rms": 0.01,
            "catatan": (
                "Embedding klip = rata-rata seluruh jendela 3 detik yang lolos "
                "ambang energi RMS. Evaluasi tetap di tingkat klip supaya "
                "sebanding dengan baseline. Agregasi diperlukan karena resep "
                "latih memetakan id splits langsung ke baris embedding, "
                "sedangkan id jendela berakhiran __w<N>."
            ),
        }, indent=2, ensure_ascii=False))
        print(f"  laporan C18: {lap}")
        print("  CATATAN: C18 juga menuntut emb_dir laporan SAMA dengan "
              "meta.json produksi, jadi ini baru lulus setelah model dari "
              "embedding ini benar-benar dipromosikan.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
