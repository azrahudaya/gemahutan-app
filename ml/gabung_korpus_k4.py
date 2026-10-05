"""Gabungkan korpus K3 dengan 3 kelas PEMICU K4 jadi satu direktori embedding.

Keluaran: ml/embeddings_k4_klip (8353 klip K3 + 112 klip pemicu) dan
ml/data/splits_k4.json (splits K3 + klip pemicu masuk LATIH saja).

Klip pemicu masuk latih saja, TIDAK ikut dievaluasi, dan itu keputusan yang
disengaja: tujuan K4 adalah memberi model tempat membuang burung pemicu, bukan
menambah kelas yang ikut dinilai. Memasukkannya ke pool evaluasi akan mengubah
komposisi pool dan membatalkan kesebandingan G2 (aturan B1).

MASALAH KESEBANDINGAN yang ditangani di sini, jangan dilewati: F1 makro
bergantung jumlah kelas. K3 punya 26 kelas, K4 punya 29, jadi
f1_macro 29 kelas TIDAK sebanding dengan f1_macro 26 kelas apa adanya. Tiga
kelas pemicu hampir pasti mudah (F1 CV pilot 0,80 sampai 1,00), jadi rata-rata
makronya akan NAIK hanya karena ada tiga kelas mudah ikut dirata-rata, bukan
karena 25 spesies target membaik. Itu kenaikan palsu.

Karena itu `ml/nilai_g2_k4.py` menghitung F1 makro HANYA pada 26 kelas yang ada
di kedua sisi. Skrip ini menuliskan daftar kelas bersama itu ke
kelas_bersama.json supaya penilainya tidak perlu menebak.

Jalankan: .venv/bin/python ml/gabung_korpus_k4.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
ML = ROOT / "ml"


def main() -> int:
    k3 = ML / "embeddings_bersuara_v3_klip"
    pem = ML / "embeddings_bersuara_pemicu_klip"
    out = ML / "embeddings_k4_klip"
    out.mkdir(parents=True, exist_ok=True)

    e3 = np.load(k3 / "embeddings.npy")
    l3 = np.load(k3 / "labels.npy")
    i3 = json.loads((k3 / "clip_ids.json").read_text())
    m3 = json.loads((k3 / "label_map.json").read_text())

    ep = np.load(pem / "embeddings.npy")
    ip = json.loads((pem / "clip_ids.json").read_text())
    mp = json.loads((pem / "label_map.json").read_text())
    lp = np.load(pem / "labels.npy")

    if e3.shape[1] != ep.shape[1]:
        print(f"ERROR dimensi beda: K3 {e3.shape[1]} vs pemicu {ep.shape[1]}")
        return 1

    dobel = set(i3) & set(ip)
    if dobel:
        print(f"ERROR: {len(dobel)} clip_id dobel antara K3 dan pemicu, mis. {sorted(dobel)[:3]}")
        return 1

    # Kelas pemicu diberi indeks SETELAH seluruh kelas K3, supaya indeks kelas
    # lama tidak bergeser. Pergeseran indeks akan membuat bobot lama dan
    # label_map lama tidak lagi cocok tanpa ada yang terlihat salah.
    inv_p = {v: k for k, v in mp.items()}
    gabung = dict(m3)
    next_idx = max(m3.values()) + 1
    for sp in sorted(mp, key=lambda s: mp[s]):
        if sp in gabung:
            print(f"ERROR: kelas pemicu {sp} sudah ada di label_map K3")
            return 1
        gabung[sp] = next_idx
        next_idx += 1

    lp_baru = np.array([gabung[inv_p[int(v)]] for v in lp], dtype=np.int32)

    emb = np.concatenate([e3, ep]).astype(np.float32)
    lab = np.concatenate([l3, lp_baru]).astype(np.int32)
    ids = list(i3) + list(ip)

    np.save(out / "embeddings.npy", emb)
    np.save(out / "labels.npy", lab)
    (out / "clip_ids.json").write_text(json.dumps(ids))
    (out / "label_map.json").write_text(json.dumps(gabung, indent=2))
    (out / "kelas_bersama.json").write_text(json.dumps(sorted(m3), indent=2))

    sp3 = json.loads((ML / "data" / "splits_v3_nd_bersih.json").read_text())
    baru = dict(sp3)
    baru["train"] = list(sp3["train"]) + list(ip)
    (ML / "data" / "splits_k4.json").write_text(json.dumps(baru, indent=2))

    print(f"embedding gabungan : {emb.shape}")
    print(f"kelas              : {len(m3)} -> {len(gabung)} (+{len(mp)} pemicu)")
    print(f"klip pemicu ke LATIH: {len(ip)}")
    print(f"train {len(sp3['train'])} -> {len(baru['train'])}, val {len(baru.get('val', []))} (tidak diubah)")
    print(f"kelas bersama untuk G2: {len(m3)}")
    print(f"keluaran: {out}, {ML / 'data' / 'splits_k4.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
