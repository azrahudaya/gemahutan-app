"""Bangun angka_resmi.json dari artefak laporan (satu sumber angka).

Membaca eval_bersarang.json, uji_independen.json, e2e.json, latensi.json,
dan MANIFEST.json. Semua angka yang ditampilkan README/proposal/API wajib
dibaca dari berkas ini.

Jalankan: python3 ml/buat_angka_resmi.py
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ML_DIR = ROOT / "ml"
REPORTS = ML_DIR / "reports"
CHECKPOINT = ML_DIR / "checkpoints"


def baca(path: Path) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            pass
    return {}


def main() -> int:
    eval_b = baca(REPORTS / "eval_bersarang.json")
    uji = baca(REPORTS / "uji_independen.json")
    e2e = baca(REPORTS / "e2e.json")
    latensi = baca(REPORTS / "latensi.json")
    manifest = baca(CHECKPOINT / "MANIFEST.json")

    # F1 CV dan CI95
    f1_cv = None
    f1_cv_ci95 = None
    agg = eval_b.get("aggregat", {})
    ci95 = eval_b.get("ci95", {})
    if "f1_macro" in agg:
        f1_cv = round(float(agg["f1_macro"]), 3)
    if "f1_macro" in ci95:
        f1_cv_ci95 = [round(float(ci95["f1_macro"]["ci95_low"]), 3),
                       round(float(ci95["f1_macro"]["ci95_high"]), 3)]

    # Uji independen
    acc_independen = None
    f1_independen = None
    jb = uji.get("jendela_terbaik", {})
    if "acc" in jb:
        acc_independen = round(float(jb["acc"]), 3)
    if "f1_macro" in jb:
        f1_independen = round(float(jb["f1_macro"]), 3)

    # E2E
    e2e_presisi = None
    e2e_recall = None
    if "agregat" in e2e:
        e2e_presisi = round(float(e2e["agregat"].get("presisi", 0)), 3)
        e2e_recall = round(float(e2e["agregat"].get("recall", 0)), 3)

    # FP pengecoh (berkas pengecoh berdeteksi / total pengecoh)
    fp_pengecoh_berkas = None
    per_korpus = e2e.get("per_korpus", {})
    if "field/other" in per_korpus:
        other = per_korpus["field/other"]
        n = other.get("n_berkas", 0)
        det = other.get("berkas_dengan_deteksi_target", 0)
        if n > 0:
            fp_pengecoh_berkas = round(det / n, 3)

    latensi_60m_s = None
    if "waktu_s" in latensi:
        latensi_60m_s = round(float(latensi["waktu_s"]), 1)

    sha256_ckpt = None
    if "files" in manifest and "best_model.npz" in manifest["files"]:
        sha256_ckpt = manifest["files"]["best_model.npz"]["sha256"]

    angka = {
        "f1_cv": f1_cv,
        "f1_cv_ci95": f1_cv_ci95,
        "acc_independen": acc_independen,
        "f1_independen": f1_independen,
        "e2e_presisi": e2e_presisi,
        "e2e_recall": e2e_recall,
        "fp_pengecoh_berkas": fp_pengecoh_berkas,
        "latensi_60m_s": latensi_60m_s,
        "sha256_checkpoint": sha256_ckpt,
        "dibuat": datetime.now(UTC).isoformat(),
    }
    (REPORTS / "angka_resmi.json").write_text(
        json.dumps(angka, indent=2, ensure_ascii=False))
    print(json.dumps(angka, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())