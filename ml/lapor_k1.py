"""Hitung bagian LAPOR sekali untuk K1 (konfirmasi lunak) memakai definisi audit.

Aturan ML_00/ML_10: pemilihan konfigurasi HANYA di bagian pilih. Bagian lapor
dihitung SEKALI untuk kandidat terpilih dan baseline, lalu ditulis apa adanya.
Skrip ini tidak memilih apa pun, hanya melapor.

Definisi yang dipakai disalin dari `ops/audit_model.py` supaya angkanya cocok
dengan apa yang akan dinilai audit penuh, bukan definisi sendiri:

- C13 FP pengecoh = proporsi berkas `field/other` bagian lapor yang punya minimal
  satu deteksi (baris 347), BUKAN FP per deteksi.
- C13 recall target = recall per DETEKSI (`metrik_berkas`, baris 275-279) pada
  baris non-`field/other` bagian lapor ditambah seluruh `uji_independen`.
- C15 ponsel iNat = presisi dan recall per deteksi pada `field/inat` bagian lapor.

Snapshot sapuan sudah memuat 285 baris bagian lapor, jadi tidak perlu
menjalankan ulang e2e: angka lapor dibaca dari snapshot yang sama yang dipakai
untuk bagian pilih, sehingga keduanya pasti dari satu proses yang sama.

Jalankan: .venv/bin/python ml/lapor_k1.py
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REP = ROOT / "ml" / "reports"


def metrik_berkas(rows: list[dict]) -> tuple[float, float]:
    """Presisi dan recall per deteksi. Disalin dari ops/audit_model.py:275."""
    tp = sum(len(set(r["terdeteksi"]) & set(r["benar"])) for r in rows)
    fp = sum(len(set(r["terdeteksi"]) - set(r["benar"])) for r in rows)
    fn = sum(len(set(r["benar"]) - set(r["terdeteksi"])) for r in rows)
    return tp / max(tp + fp, 1), tp / max(tp + fn, 1)


def hitung(path: Path) -> dict:
    d = json.loads(path.read_text())
    rows = d.get("per_berkas", [])
    lapor = [r for r in rows if r.get("bagian") == "lapor"]

    peng = [r for r in lapor if r["korpus"] == "field/other"]
    targ = [r for r in rows if r["korpus"] != "field/other"
            and (r.get("bagian") == "lapor" or r["korpus"] == "uji_independen")]
    inat = [r for r in lapor if r["korpus"] == "field/inat"]

    fp_berkas = sum(1 for r in peng if r["terdeteksi"]) / max(len(peng), 1)
    _, rec = metrik_berkas(targ)
    p_inat, r_inat = metrik_berkas(inat)

    return {
        "snapshot": str(path.resolve().relative_to(ROOT)),
        "sha256_checkpoint": d.get("sha256_checkpoint"),
        "n_lapor": len(lapor),
        "c13_fp_pengecoh_berkas": round(fp_berkas, 4),
        "c13_n_pengecoh": len(peng),
        "c13_recall_target": round(rec, 4),
        "c13_n_target": len(targ),
        "c13_lulus": bool(fp_berkas <= 0.15 and rec >= 0.70),
        "c13_batas_nilai7": bool(fp_berkas <= 0.25 and rec >= 0.65),
        "c15_inat_presisi": round(p_inat, 4),
        "c15_inat_recall": round(r_inat, 4),
        "c15_n_inat": len(inat),
        "c15_lulus": bool(p_inat >= 0.75 and r_inat >= 0.62),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("snapshot", nargs="+")
    ap.add_argument("--nama", nargs="*", default=None)
    ap.add_argument("--out", default=str(REP / "k1_lapor.json"))
    a = ap.parse_args()

    nama = a.nama or [Path(s).stem for s in a.snapshot]
    hasil = {}
    for lbl, s in zip(nama, a.snapshot, strict=True):
        hasil[lbl] = hitung(Path(s))

    Path(a.out).write_text(json.dumps(hasil, indent=2, ensure_ascii=False))

    print(f"{'konfigurasi':20s} {'C13 FP':>8s} {'C13 rec':>8s} {'C13':>7s} {'nilai7':>7s} "
          f"{'C15 P':>7s} {'C15 R':>7s} {'C15':>6s}")
    for lbl, h in hasil.items():
        print(f"{lbl:20s} {h['c13_fp_pengecoh_berkas']:8.4f} {h['c13_recall_target']:8.4f} "
              f"{'LULUS' if h['c13_lulus'] else 'gagal':>7s} "
              f"{'ya' if h['c13_batas_nilai7'] else 'tidak':>7s} "
              f"{h['c15_inat_presisi']:7.4f} {h['c15_inat_recall']:7.4f} "
              f"{'LULUS' if h['c15_lulus'] else 'gagal':>6s}")
    print(f"\nn pengecoh lapor {hasil[nama[0]]['c13_n_pengecoh']}, "
          f"n target {hasil[nama[0]]['c13_n_target']}, n iNat {hasil[nama[0]]['c15_n_inat']}")
    print("Ditulis:", a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
