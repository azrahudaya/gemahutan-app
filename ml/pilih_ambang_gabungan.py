"""Pilih ulang ambang per spesies di bagian PILIH, target presisi >= 0,80 (G-ambang).

Kenapa ini varian terpisah dari G, bukan pengganti: ambang produksi dipilih di
ml/latih_produksi.py baris 184-205 dengan F1 MAKSIMUM pada val. F1 menyeimbangkan
presisi dan recall, jadi ia menerima banyak deteksi palsu selama recall-nya ikut
naik. Syarat C13 tidak simetris seperti itu: FP dibatasi keras (<= 0,25 untuk
nilai 7) sedangkan recall hanya perlu >= 0,65. Jadi ambang yang optimal untuk F1
bukan ambang yang optimal untuk C13.

Dipilih HANYA dari bagian pilih, sesuai aturan ML_10. Bagian lapor tidak dilihat
sama sekali di sini.

CARA KERJA dan batasnya, supaya tidak ada yang mengira ini lebih sakti dari
kenyataannya: skor diambil dari cache deteksi run G (ml/runs/<id>/cache_e2e).
Cache itu berisi deteksi SETELAH ambang produksi diterapkan, jadi skrip ini
hanya bisa MENAIKKAN ambang, tidak menurunkannya. Untuk tujuan menekan FP itu
justru arah yang dibutuhkan, tapi artinya ambang hasil skrip ini selalu >=
ambang produksi, dan itu dicatat di keluaran.

Definisi presisi yang dipakai: per DETEKSI, bukan per berkas. Satu deteksi
spesies S di berkas F dihitung benar kalau S ada di daftar `benar` berkas F.
Spesies dengan deteksi terlalu sedikit di bagian pilih tidak bisa diestimasi dan
ambangnya DIBIARKAN seperti produksi, bukan dinaikkan dengan menebak.

Jalankan:
  .venv/bin/python ml/pilih_ambang_gabungan.py --run-id g_k3_k1 --out-id g_ambang
"""
from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ML = ROOT / "ml"
REP = ML / "reports"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True, help="run G yang cache-nya dipakai")
    ap.add_argument("--out-id", required=True, help="nama run keluaran untuk thresholds baru")
    ap.add_argument("--target-presisi", type=float, default=0.80)
    ap.add_argument("--min-deteksi", type=int, default=5,
                    help="minimum deteksi di bagian pilih supaya presisi bisa diestimasi")
    ap.add_argument("--ambang-produksi", default=str(REP / "thresholds.json"))
    a = ap.parse_args()

    run_dir = ML / "runs" / a.run_id
    cache_dir = run_dir / "cache_e2e"
    e2e = json.loads((run_dir / "e2e.json").read_text())

    prod = json.loads(Path(a.ambang_produksi).read_text())

    # Kumpulkan skor per spesies HANYA dari berkas bagian pilih.
    skor: dict[str, list[tuple[float, bool]]] = collections.defaultdict(list)
    n_berkas = 0
    for r in e2e.get("per_berkas", []):
        if r.get("bagian") != "pilih":
            continue
        rel = r["berkas"]
        cf = cache_dir / f"{rel.replace('/', '__')}__.json"
        if not cf.exists():
            continue
        n_berkas += 1
        benar = set(r["benar"])
        for d in json.loads(cf.read_text()):
            sp = d["species"]
            if sp in prod:
                skor[sp].append((float(d["confidence"]), sp in benar))

    baru = dict(prod)
    rincian = {}
    for sp, t_prod in prod.items():
        if sp == "_negative":
            rincian[sp] = {"keputusan": "tidak disentuh (bukan kelas target)"}
            continue
        pasangan = sorted(skor.get(sp, []), key=lambda x: -x[0])
        n = len(pasangan)
        if n < a.min_deteksi:
            rincian[sp] = {
                "n_deteksi_pilih": n,
                "keputusan": f"dibiarkan di ambang produksi {t_prod:.4f}, deteksi < {a.min_deteksi}",
                "ambang_baru": t_prod,
            }
            continue

        tp_awal = sum(1 for _, b in pasangan if b)
        pres_awal = tp_awal / n

        # Naikkan ambang sampai presisi mencapai target. Kandidat ambang = skor
        # yang benar-benar muncul, supaya tidak memilih angka yang tak terwakili.
        terbaik = None
        for c in sorted({p[0] for p in pasangan}):
            lolos = [b for s, b in pasangan if s >= c]
            if not lolos:
                continue
            pres = sum(lolos) / len(lolos)
            if pres >= a.target_presisi:
                terbaik = (c, pres, len(lolos), sum(lolos))
                break

        if terbaik is None:
            # Tidak ada ambang yang mencapai target, termasuk ambang tertinggi.
            tertinggi = max(s for s, _ in pasangan)
            rincian[sp] = {
                "n_deteksi_pilih": n,
                "presisi_pada_ambang_produksi": round(pres_awal, 4),
                "keputusan": "TARGET TIDAK TERCAPAI pada ambang mana pun, dipakai skor tertinggi",
                "ambang_baru": float(tertinggi),
            }
            baru[sp] = float(tertinggi)
            continue

        c, pres, n_lolos, n_tp = terbaik
        ambang_baru = max(float(c), float(t_prod))
        rincian[sp] = {
            "n_deteksi_pilih": n,
            "presisi_pada_ambang_produksi": round(pres_awal, 4),
            "ambang_produksi": round(float(t_prod), 4),
            "ambang_baru": round(ambang_baru, 4),
            "presisi_pada_ambang_baru": round(pres, 4),
            "n_deteksi_lolos": n_lolos,
            "n_benar_lolos": int(n_tp),
            "keputusan": "naik" if ambang_baru > t_prod else "tidak berubah",
        }
        baru[sp] = ambang_baru

    out_dir = ML / "runs" / a.out_id
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "thresholds.json").write_text(json.dumps(baru, indent=2))

    naik = sum(1 for v in rincian.values() if v.get("keputusan") == "naik")
    gagal = sum(1 for v in rincian.values() if "TIDAK TERCAPAI" in str(v.get("keputusan")))
    sedikit = sum(1 for v in rincian.values() if "deteksi <" in str(v.get("keputusan")))

    lap = {
        "run_sumber": a.run_id,
        "n_berkas_pilih_dipakai": n_berkas,
        "target_presisi": a.target_presisi,
        "min_deteksi": a.min_deteksi,
        "n_spesies_ambang_naik": naik,
        "n_spesies_target_tidak_tercapai": gagal,
        "n_spesies_deteksi_terlalu_sedikit": sedikit,
        "catatan_batas": (
            "Skor berasal dari cache deteksi yang sudah melewati ambang produksi, "
            "jadi ambang hanya bisa NAIK. Ambang baru selalu >= ambang produksi."
        ),
        "thresholds_baru": str((out_dir / "thresholds.json").relative_to(ROOT)),
        "rincian": rincian,
    }
    out_json = REP / "gabungan" / f"{a.out_id}_pemilihan_ambang.json"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(lap, indent=2, ensure_ascii=False))

    print(f"berkas pilih dipakai        : {n_berkas}")
    print(f"spesies ambang NAIK         : {naik}")
    print(f"spesies target tak tercapai : {gagal}")
    print(f"spesies deteksi < {a.min_deteksi}        : {sedikit}")
    print(f"thresholds baru: {out_dir / 'thresholds.json'}")
    print(f"laporan        : {out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
