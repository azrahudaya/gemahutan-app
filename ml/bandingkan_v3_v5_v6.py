"""Bandingkan v3, v5, v6 pada metrik G2 dan pool yang sama.

Output:
- ml/reports/banding_v3_v5_v6.md
- ml/reports/banding_v3_v5_v6.json
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "ml" / "runs" / "l6"
OUT_JSON = ROOT / "ml" / "reports" / "banding_v3_v5_v6.json"
OUT_MD = ROOT / "ml" / "reports" / "banding_v3_v5_v6.md"


def _load(path: Path) -> dict:
    return json.loads(path.read_text())


def _lapor(e2e: dict) -> dict:
    rows = [r for r in e2e["per_berkas"] if r.get("bagian") == "lapor"]
    t = [r for r in rows if r.get("korpus") in {"field/inat", "field/xc_noisy"}]
    o = [r for r in rows if r.get("korpus") == "field/other"]

    tp = fn = 0
    for r in t:
        benar = set(r.get("benar", []))
        det = set(r.get("terdeteksi", []))
        tp += len(benar & det)
        fn += len(benar - det)
    rec = 0.0 if (tp + fn) == 0 else tp / (tp + fn)
    fp = sum(1 for r in o if r.get("terdeteksi"))
    rate = 0.0 if not o else fp / len(o)
    return {
        "n_lapor": len(rows),
        "n_lapor_target": len(t),
        "n_lapor_other": len(o),
        "fp_lapor_berkas": fp,
        "fp_lapor_rate": rate,
        "recall_target_lapor": rec,
    }


def _model_row(name: str, cv: dict, indep: dict, e2e: dict, g2: dict | None) -> dict:
    lap = _lapor(e2e)
    row = {
        "model": name,
        "f1_cv": cv["aggregat"]["f1_macro"],
        "acc_indep": indep["jendela_terbaik"]["acc"],
        "fp_lapor_rate": lap["fp_lapor_rate"],
        "fp_lapor_berkas": lap["fp_lapor_berkas"],
        "n_lapor_other": lap["n_lapor_other"],
        "recall_target_lapor": lap["recall_target_lapor"],
        "pool_cv": cv.get("pool"),
        "pool_e2e": e2e.get("pool"),
        "pool_indep": indep.get("pool"),
    }
    if g2:
        row["g2_lulus"] = g2.get("lulus")
        row["g2_checks"] = {k: v.get("lulus") for k, v in g2.get("checks", {}).items()}
    return row


def main() -> int:
    v3_cv = _load(RUNS / "v3/eval_bersarang_v3.json")
    v5_cv = _load(RUNS / "v5/eval_bersarang_v5.json")
    v6_cv = _load(RUNS / "v6/eval_bersarang_v6.json")

    v3_ind = _load(RUNS / "v3/uji_independen_v3.json")
    v5_ind = _load(RUNS / "v5/uji_independen.json")
    v6_ind = _load(RUNS / "v6/uji_independen.json")

    v3_e2e = _load(RUNS / "v3/e2e_v3.json")
    v5_e2e = _load(RUNS / "v5/e2e.json")
    v6_e2e = _load(RUNS / "v6/e2e.json")

    v5_g2 = _load(RUNS / "v5/gerbang_g2.json")
    v6_g2 = _load(RUNS / "v6/gerbang_g2.json")

    rows = [
        _model_row("v3", v3_cv, v3_ind, v3_e2e, None),
        _model_row("v5", v5_cv, v5_ind, v5_e2e, v5_g2),
        _model_row("v6", v6_cv, v6_ind, v6_e2e, v6_g2),
    ]

    v3 = rows[0]
    for r in rows[1:]:
        r["delta_vs_v3"] = {
            "f1_cv": r["f1_cv"] - v3["f1_cv"],
            "acc_indep": r["acc_indep"] - v3["acc_indep"],
            "fp_lapor_rate": r["fp_lapor_rate"] - v3["fp_lapor_rate"],
            "recall_target_lapor": r["recall_target_lapor"] - v3["recall_target_lapor"],
        }

    payload = {
        "ringkas": rows,
        "pool_sha": {
            "e2e": rows[0]["pool_e2e"]["sha256_daftar_berkas"],
            "cv_xc": rows[0]["pool_cv"]["sha256_xc_ids"],
            "indep": rows[0]["pool_indep"]["sha256_clip_ids"],
        },
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False))

    md = []
    md.append("# Banding v3, v5, v6 (G2)")
    md.append("")
    md.append("Pool yang dipakai:")
    md.append(f"- E2E sha256 daftar berkas: {payload['pool_sha']['e2e']}")
    md.append(f"- CV XC sha256 id: {payload['pool_sha']['cv_xc']}")
    md.append(f"- Independen sha256 clip id: {payload['pool_sha']['indep']}")
    md.append("")
    md.append("| Model | F1 CV | Δ vs v3 | FP lapor (berkas/rasio) | Δ FP rasio | Recall target lapor | Δ recall | Acc independen | Δ acc | G2 |")
    md.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---|")

    for i, r in enumerate(rows):
        if i == 0:
            md.append(
                f"| {r['model']} | {r['f1_cv']:.4f} | 0.0000 | {r['fp_lapor_berkas']}/{r['n_lapor_other']} ({r['fp_lapor_rate']:.4f}) | 0.0000 | {r['recall_target_lapor']:.4f} | 0.0000 | {r['acc_indep']:.4f} | 0.0000 | baseline |"
            )
        else:
            d = r["delta_vs_v3"]
            md.append(
                f"| {r['model']} | {r['f1_cv']:.4f} | {d['f1_cv']:+.4f} | {r['fp_lapor_berkas']}/{r['n_lapor_other']} ({r['fp_lapor_rate']:.4f}) | {d['fp_lapor_rate']:+.4f} | {r['recall_target_lapor']:.4f} | {d['recall_target_lapor']:+.4f} | {r['acc_indep']:.4f} | {d['acc_indep']:+.4f} | {'LULUS' if r.get('g2_lulus') else 'GAGAL'} |"
            )

    md.append("")
    md.append("## Status syarat G2")
    for r in rows[1:]:
        md.append("")
        md.append(f"### {r['model']}")
        for code, ok in r.get("g2_checks", {}).items():
            md.append(f"- {code}: {'LULUS' if ok else 'GAGAL'}")

    OUT_MD.write_text("\n".join(md) + "\n")

    print(f"Output: {OUT_JSON}")
    print(f"Output: {OUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
