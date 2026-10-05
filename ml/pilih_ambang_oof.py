"""Pilih ambang per spesies dari prediksi OOF CV bersarang (butir 3 audit 2 Okt).

Kenapa diganti dari cara lama: `ml/pilih_ambang_gabungan.py` memilih ambang dari
bagian pilih, yaitu 59 berkas pengecoh dan 104 berkas target. Hasilnya overfit,
dan selisihnya terukur: FP bagian pilih 0,1017 versus FP bagian lapor 0,3158 pada
konfigurasi yang sama. OOF CV bersarang memberi 892 klip, jadi estimasi presisi
per spesies jauh lebih stabil.

Sah dipakai untuk memilih karena OOF berasal dari data LATIH yang diprediksi
out-of-fold dengan grup perekam dipisah (StratifiedGroupKFold), bukan dari bagian
lapor. Bagian lapor tidak dilihat sama sekali di sini.

ATURAN: untuk tiap spesies, ambil ambang TERENDAH yang presisinya >= target.
Terendah, bukan tertinggi, supaya recall tidak dikorbankan lebih dari yang perlu.

TIGA BATAS yang harus dibaca bersama angkanya, jangan dilewati:

1. Distribusi OOF bukan distribusi lapangan. OOF berisi 892 klip Xeno-canto dari
   25 spesies target, sedangkan deteksi palsu di e2e datang dari klip pengecoh
   spesies LAIN yang direkam di lapangan. Jadi presisi OOF menjawab "kalau model
   bilang spesies S, seberapa sering benar di antara klip XC target", bukan
   "seberapa sering pengecoh lapangan dikira S". Ambang dari OOF lebih stabil
   karena datanya 15 kali lebih banyak, tapi tidak otomatis memindahkan FP
   lapangan ke angka yang sama.

2. OOF tingkat KLIP, e2e tingkat JENDELA. Resep K3 merata-ratakan jendela
   bersuara per klip, sedangkan CascadeEngine menerapkan ambang per jendela.
   Rata-rata meredam puncak, jadi skor jendela cenderung lebih ekstrem daripada
   skor klip. Arah efeknya sudah diukur di
   ml/reports/k3_bersuara/ketaksesuaian_latih_saji.txt (selisih +0,0079, kecil).

3. Ambang hasil skrip ini TIDAK dibatasi >= ambang produksi, berbeda dari
   pilih_ambang_gabungan.py. Di sana skor dibaca dari cache deteksi yang sudah
   lewat ambang produksi sehingga ambang hanya bisa naik. Di sini skor OOF utuh,
   jadi ambang bisa turun juga. Yang turun dicatat eksplisit di laporan.

Jalankan:
  .venv/bin/python ml/pilih_ambang_oof.py --target-presisi 0.80 --out-id g_oof80
  .venv/bin/python ml/pilih_ambang_oof.py --target-presisi 0.70 --out-id g_oof70
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
ML = ROOT / "ml"
REP = ML / "reports"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--oof", default=str(ML / "runs" / "k3_bersuara" / "oof_bersarang.npz"))
    ap.add_argument("--label-map", default=str(ML / "runs" / "k3_bersuara_model" / "label_map.json"))
    ap.add_argument("--ambang-produksi", default=str(REP / "thresholds.json"))
    ap.add_argument("--target-presisi", type=float, required=True)
    ap.add_argument("--out-id", required=True)
    ap.add_argument("--min-dukungan", type=int, default=5,
                    help="minimum contoh positif OOF supaya presisi bisa diestimasi")
    a = ap.parse_args()

    d = np.load(a.oof)
    probs, y = d["probs"], d["y"]
    label_map = json.loads(Path(a.label_map).read_text())
    prod = json.loads(Path(a.ambang_produksi).read_text())

    baru = dict(prod)
    rincian = {}
    n_naik = n_turun = n_sama = n_gagal = n_sedikit = 0

    for nama, kelas in sorted(label_map.items(), key=lambda x: x[1]):
        if nama == "_negative":
            rincian[nama] = {"keputusan": "tidak disentuh (bukan kelas target)"}
            continue
        if nama not in prod:
            rincian[nama] = {"keputusan": "tidak ada di thresholds produksi, dilewati"}
            continue

        t_prod = float(prod[nama])
        skor = probs[:, kelas]
        positif = (y == kelas)
        n_pos = int(positif.sum())

        if n_pos < a.min_dukungan:
            n_sedikit += 1
            rincian[nama] = {
                "n_positif_oof": n_pos,
                "keputusan": f"dibiarkan di ambang produksi {t_prod:.4f}, dukungan < {a.min_dukungan}",
                "ambang_baru": round(t_prod, 4),
            }
            continue

        # Kandidat ambang = skor yang benar-benar muncul, dari rendah ke tinggi.
        # Diambil yang TERENDAH yang presisinya memenuhi target.
        kandidat = np.unique(skor)
        terpilih = None
        for t in kandidat:
            lolos = skor >= t
            if not lolos.any():
                continue
            tp = int((lolos & positif).sum())
            pres = tp / int(lolos.sum())
            if pres >= a.target_presisi:
                rec = tp / n_pos
                terpilih = (float(t), pres, rec, int(lolos.sum()), tp)
                break

        if terpilih is None:
            n_gagal += 1
            tertinggi = float(kandidat[-1])
            lolos = skor >= tertinggi
            tp = int((lolos & positif).sum())
            rincian[nama] = {
                "n_positif_oof": n_pos,
                "ambang_produksi": round(t_prod, 4),
                "keputusan": "TARGET TIDAK TERCAPAI pada ambang mana pun, dipakai skor tertinggi",
                "ambang_baru": round(tertinggi, 4),
                "presisi_pada_ambang_baru": round(tp / max(int(lolos.sum()), 1), 4),
            }
            baru[nama] = tertinggi
            continue

        t, pres, rec, n_lolos, tp = terpilih
        arah = "naik" if t > t_prod + 1e-9 else ("turun" if t < t_prod - 1e-9 else "tidak berubah")
        if arah == "naik":
            n_naik += 1
        elif arah == "turun":
            n_turun += 1
        else:
            n_sama += 1

        rincian[nama] = {
            "n_positif_oof": n_pos,
            "ambang_produksi": round(t_prod, 4),
            "ambang_baru": round(t, 4),
            "presisi_oof": round(pres, 4),
            "recall_oof": round(rec, 4),
            "n_deteksi_oof": n_lolos,
            "n_benar_oof": tp,
            "keputusan": arah,
        }
        baru[nama] = t

    out_dir = ML / "runs" / a.out_id
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "thresholds.json").write_text(json.dumps(baru, indent=2))

    lap = {
        "sumber_ambang": "OOF CV bersarang (bukan bagian pilih, bukan bagian lapor)",
        "oof": str(Path(a.oof).relative_to(ROOT)),
        "n_klip_oof": int(probs.shape[0]),
        "target_presisi": a.target_presisi,
        "aturan": "ambang TERENDAH yang presisi OOF >= target",
        "min_dukungan": a.min_dukungan,
        "n_spesies_naik": n_naik,
        "n_spesies_turun": n_turun,
        "n_spesies_tidak_berubah": n_sama,
        "n_spesies_target_tidak_tercapai": n_gagal,
        "n_spesies_dukungan_kurang": n_sedikit,
        "batas_yang_harus_dibaca": [
            "OOF 892 klip Xeno-canto target, bukan pengecoh lapangan: presisi OOF "
            "bukan ramalan langsung FP lapangan.",
            "OOF tingkat klip (rata-rata jendela), e2e menerapkan ambang per jendela.",
            "Ambang boleh TURUN di sini, berbeda dari pilih_ambang_gabungan.py.",
        ],
        "thresholds_baru": str((out_dir / "thresholds.json").relative_to(ROOT)),
        "rincian": rincian,
    }
    out_json = REP / "gabungan" / f"{a.out_id}_pemilihan_ambang.json"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(lap, indent=2, ensure_ascii=False))

    print(f"OOF: {probs.shape[0]} klip, target presisi {a.target_presisi}")
    print(f"  naik {n_naik}, turun {n_turun}, tidak berubah {n_sama}, "
          f"target tak tercapai {n_gagal}, dukungan kurang {n_sedikit}")
    print(f"thresholds: {out_dir / 'thresholds.json'}")
    print(f"laporan   : {out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
