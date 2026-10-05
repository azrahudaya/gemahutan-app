"""Hitung gerbang G2 otomatis untuk kandidat model.

G2:
- F1 CV tidak turun > 0,02
- Deteksi palsu bagian lapor tidak naik
- Recall target bagian lapor tidak turun > 0,03
- Akurasi uji independen tidak turun > 0,03
- F1 per spesies dari CV tidak ada yang turun > 0,10

Jalankan:
python ml/gerbang.py --kandidat-dir ml/runs/l6/v6 --out ml/runs/l6/v6/gerbang_g2.json

Baseline bawaan: ml/runs/l6/produksi (paket produksi).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def _f1_binary(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    tp = int(np.sum((y_true == 1) & (y_pred == 1)))
    fp = int(np.sum((y_true == 0) & (y_pred == 1)))
    fn = int(np.sum((y_true == 1) & (y_pred == 0)))
    d = 2 * tp + fp + fn
    return 0.0 if d == 0 else (2 * tp) / d


def _f1_per_species_from_oof(oof_npz: Path, eval_bersarang_json: Path) -> dict[str, float]:
    d = np.load(oof_npz, allow_pickle=False)
    probs = d["probs"]
    y = d["y"].astype(int)
    pred = np.argmax(probs, axis=1).astype(int)

    info = _load_json(eval_bersarang_json)
    emb_label_map = None

    emb_dir = info.get("emb_dir")
    candidates: list[Path] = []
    if emb_dir:
        p = Path(emb_dir)
        candidates.append((p if p.is_absolute() else Path.cwd() / p) / "label_map.json")

    split_file = info.get("splits_file")
    if split_file:
        sp = Path(split_file)
        if not sp.is_absolute():
            sp = Path.cwd() / sp
        if "splits_v3" in sp.name:
            candidates.append(Path.cwd() / "ml/embeddings_v3/label_map.json")
        if "splits_v5" in sp.name:
            candidates.append(Path.cwd() / "ml/embeddings_v5/label_map.json")
        if "splits_v6" in sp.name:
            candidates.append(Path.cwd() / "ml/embeddings_v6/label_map.json")

    for c in candidates:
        if c.exists():
            emb_label_map = _load_json(c)
            break

    if not emb_label_map:
        raise FileNotFoundError("label_map.json tidak ditemukan dari eval_bersarang (emb_dir/splits_file)")

    inv = {int(v): k for k, v in emb_label_map.items()}
    neg_idx = int(emb_label_map.get("_negative", -1))

    out: dict[str, float] = {}
    for cls in sorted(set(y.tolist())):
        if cls == neg_idx:
            continue
        yb = (y == cls).astype(int)
        pb = (pred == cls).astype(int)
        out[inv.get(cls, str(cls))] = float(_f1_binary(yb, pb))
    return out


def _lapor_metrics(e2e_json: Path) -> dict:
    d = _load_json(e2e_json)
    rows = [r for r in d.get("per_berkas", []) if r.get("bagian") == "lapor"]

    target_rows = [r for r in rows if r.get("korpus") in {"field/inat", "field/xc_noisy"}]
    other_rows = [r for r in rows if r.get("korpus") == "field/other"]

    tp = 0
    fn = 0
    for r in target_rows:
        benar = set(r.get("benar", []))
        det = set(r.get("terdeteksi", []))
        tp += len(benar & det)
        fn += len(benar - det)
    recall_target = 0.0 if (tp + fn) == 0 else tp / (tp + fn)

    fp_files = sum(1 for r in other_rows if len(r.get("terdeteksi", [])) > 0)
    fp_rate = 0.0 if len(other_rows) == 0 else fp_files / len(other_rows)

    return {
        "n_lapor": len(rows),
        "n_lapor_target": len(target_rows),
        "n_lapor_other": len(other_rows),
        "fp_lapor_berkas": fp_files,
        "fp_lapor_rate": fp_rate,
        "recall_target_lapor": recall_target,
    }


def _pick_file(dir_path: Path, names: list[str]) -> Path:
    for name in names:
        p = dir_path / name
        if p.exists():
            return p
    raise FileNotFoundError(f"Tidak menemukan file kandidat di {dir_path}: {names}")


def hitung_g2(baseline_dir: Path, kandidat_dir: Path) -> dict:
    """Hitung gerbang G2. G2-6 otomatis TIDAK DINILAI jika G2-1 sampai G2-5 ada yang gagal."""
    base_cv_path = _pick_file(baseline_dir, ["eval_bersarang_v3.json", "eval_bersarang.json"])
    k_cv_path = _pick_file(kandidat_dir, ["eval_bersarang.json", "eval_bersarang_v5.json", "eval_bersarang_v6.json"])
    base_indep_path = _pick_file(baseline_dir, ["uji_independen_v3.json", "uji_independen.json"])
    k_indep_path = _pick_file(kandidat_dir, ["uji_independen.json"])
    base_e2e_path = _pick_file(baseline_dir, ["e2e_v3.json", "e2e.json"])
    k_e2e_path = _pick_file(kandidat_dir, ["e2e.json"])

    base_cv = _load_json(base_cv_path)
    k_cv = _load_json(k_cv_path)
    base_indep = _load_json(base_indep_path)
    k_indep = _load_json(k_indep_path)

    base_lapor = _lapor_metrics(base_e2e_path)
    k_lapor = _lapor_metrics(k_e2e_path)

    base_f1_cv = float(base_cv["aggregat"]["f1_macro"])
    k_f1_cv = float(k_cv["aggregat"]["f1_macro"])

    base_acc_indep = float(base_indep["jendela_terbaik"]["acc"])
    k_acc_indep = float(k_indep["jendela_terbaik"]["acc"])

    base_oof_path = _pick_file(baseline_dir, ["oof_bersarang_v3.npz", "oof_bersarang.npz"])
    k_oof_path = _pick_file(kandidat_dir, ["oof_bersarang.npz", "oof_bersarang_v5.npz", "oof_bersarang_v6.npz"])

    base_f1_sp = _f1_per_species_from_oof(base_oof_path, base_cv_path)
    k_f1_sp = _f1_per_species_from_oof(k_oof_path, k_cv_path)

    common_sp = sorted(set(base_f1_sp.keys()) & set(k_f1_sp.keys()))
    drops = {
        sp: float(k_f1_sp[sp] - base_f1_sp[sp])
        for sp in common_sp
    }
    fail_species = {sp: d for sp, d in drops.items() if d < -0.10}

    checks = {
        "G2-1": {
            "nama": "F1 CV tidak turun > 0,02",
            "batas": -0.02,
            "delta": k_f1_cv - base_f1_cv,
            "lulus": (k_f1_cv - base_f1_cv) >= -0.02,
            "baseline": base_f1_cv,
            "kandidat": k_f1_cv,
        },
        "G2-2": {
            "nama": "Deteksi palsu lapor tidak naik",
            "delta": k_lapor["fp_lapor_rate"] - base_lapor["fp_lapor_rate"],
            "lulus": k_lapor["fp_lapor_rate"] <= base_lapor["fp_lapor_rate"],
            "baseline": base_lapor,
            "kandidat": k_lapor,
        },
        "G2-3": {
            "nama": "Recall target lapor tidak turun > 0,03",
            "batas": -0.03,
            "delta": k_lapor["recall_target_lapor"] - base_lapor["recall_target_lapor"],
            "lulus": (k_lapor["recall_target_lapor"] - base_lapor["recall_target_lapor"]) >= -0.03,
            "baseline": base_lapor["recall_target_lapor"],
            "kandidat": k_lapor["recall_target_lapor"],
        },
        "G2-4": {
            "nama": "Akurasi independen tidak turun > 0,03",
            "batas": -0.03,
            "delta": k_acc_indep - base_acc_indep,
            "lulus": (k_acc_indep - base_acc_indep) >= -0.03,
            "baseline": base_acc_indep,
            "kandidat": k_acc_indep,
        },
        "G2-5": {
            "nama": "F1 per spesies CV tidak ada turun > 0,10",
            "n_spesies": len(common_sp),
            "min_delta": min(drops.values()) if drops else 0.0,
            "gagal_spesies": fail_species,
            "lulus": len(fail_species) == 0,
        },
    }

    # G2-6: TIDAK DINILAI jika G2-1 sampai G2-5 ada yang gagal
    g25_all_pass = all(checks[k].get("lulus", False) for k in ["G2-1", "G2-2", "G2-3", "G2-4", "G2-5"])
    checks["G2-6"] = {
        "nama": "Audit C01-C12 lulus",
        "lulus": False,
        "catatan": "menunggu audit manual" if g25_all_pass else "TIDAK DINILAI (G2-1 sampai G2-5 ada yang gagal)",
    }

    lulus = all(v.get("lulus", False) for v in checks.values())

    return {
        "gerbang": "G2",
        "lulus": lulus,
        "checks": checks,
        "pool": {
            "cv_baseline": base_cv.get("pool"),
            "cv_kandidat": k_cv.get("pool"),
            "e2e_baseline": _load_json(base_e2e_path).get("pool"),
            "e2e_kandidat": _load_json(kandidat_dir / "e2e.json").get("pool"),
            "indep_baseline": base_indep.get("pool"),
            "indep_kandidat": k_indep.get("pool"),
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline-dir", default="ml/runs/l6/produksi",
                    help="Direktori baseline (bawaan: ml/runs/l6/produksi)")
    ap.add_argument("--kandidat-dir", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    result = hitung_g2(
        Path(args.baseline_dir),
        Path(args.kandidat_dir),
    )

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False))

    print(f"G2 lulus: {result['lulus']}")
    for kode, cek in result["checks"].items():
        print(f"  {kode}: {cek['lulus']} - {cek['nama']}")
    print(f"Output: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
