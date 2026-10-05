from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from ml.gerbang import hitung_g2


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def _make_eval_json(path: Path, emb_dir: Path, f1_cv: float, splits_file: str) -> None:
    _write_json(
        path,
        {
            "emb_dir": str(emb_dir),
            "splits_file": splits_file,
            "aggregat": {"f1_macro": f1_cv},
            "pool": {
                "n_xc": 10,
                "sha256_xc_ids": "abc",
                "n_non_xc": 3,
                "sha256_non_xc_ids": "def",
            },
        },
    )


def _make_oof_npz(path: Path, probs: np.ndarray, y: np.ndarray) -> None:
    grup = np.array(["g1"] * len(y), dtype="<U2")
    lipatan = np.zeros(len(y), dtype=np.int32)
    np.savez(path, probs=probs.astype(np.float32), y=y.astype(np.int32), grup=grup, lipatan=lipatan)


def _make_indep_json(path: Path, acc: float) -> None:
    _write_json(path, {"jendela_terbaik": {"acc": acc}, "pool": {"n_klip": 6, "sha256_clip_ids": "xyz"}})


def _make_e2e_json(path: Path, target_hits: int, target_total: int, other_hits: int, other_total: int) -> None:
    rows = []
    for i in range(target_total):
        det = ["A"] if i < target_hits else []
        rows.append(
            {
                "bagian": "lapor",
                "korpus": "field/inat",
                "benar": ["A"],
                "terdeteksi": det,
                "nontarget": [],
                "berkas": f"t{i}",
            }
        )
    for i in range(other_total):
        det = ["A"] if i < other_hits else []
        rows.append(
            {
                "bagian": "lapor",
                "korpus": "field/other",
                "benar": [],
                "terdeteksi": det,
                "nontarget": [],
                "berkas": f"o{i}",
            }
        )
    _write_json(path, {"per_berkas": rows, "pool": {"n_lapor": len(rows)}})


def _setup_tree(tmp_path: Path):
    base = tmp_path / "base"
    cand = tmp_path / "cand"
    emb = tmp_path / "emb"
    emb.mkdir(parents=True)
    _write_json(
        emb / "label_map.json",
        {"A": 0, "B": 1, "C": 2, "_negative": 3},
    )
    return base, cand, emb


def test_gerbang_g2_lulus(tmp_path: Path):
    base, cand, emb = _setup_tree(tmp_path)

    _make_eval_json(base / "eval_bersarang_v3.json", emb, 0.70, "ml/data/splits_v3.json")
    _make_eval_json(cand / "eval_bersarang.json", emb, 0.69, "ml/data/splits_v6.json")

    y = np.array([0, 0, 1, 1, 2, 2])
    probs_base = np.array(
        [
            [0.9, 0.05, 0.03, 0.02],
            [0.8, 0.10, 0.05, 0.05],
            [0.1, 0.8, 0.05, 0.05],
            [0.1, 0.7, 0.1, 0.1],
            [0.1, 0.1, 0.7, 0.1],
            [0.1, 0.1, 0.8, 0.0],
        ]
    )
    probs_cand = np.array(
        [
            [0.9, 0.05, 0.03, 0.02],
            [0.55, 0.35, 0.05, 0.05],
            [0.1, 0.8, 0.05, 0.05],
            [0.2, 0.6, 0.1, 0.1],
            [0.2, 0.1, 0.6, 0.1],
            [0.2, 0.1, 0.65, 0.05],
        ]
    )
    _make_oof_npz(base / "oof_bersarang_v3.npz", probs_base, y)
    _make_oof_npz(cand / "oof_bersarang.npz", probs_cand, y)

    _make_indep_json(base / "uji_independen_v3.json", 0.75)
    _make_indep_json(cand / "uji_independen.json", 0.73)

    _make_e2e_json(base / "e2e_v3.json", target_hits=8, target_total=10, other_hits=2, other_total=10)
    _make_e2e_json(cand / "e2e.json", target_hits=8, target_total=10, other_hits=2, other_total=10)

    r = hitung_g2(base, cand)
    # G2-6 selalu False (menunggu audit manual atau TIDAK DINILAI),
    # jadi overall lulus = False
    assert r["lulus"] is False
    # Tapi G2-1 sampai G2-5 semua lulus
    for k in ["G2-1", "G2-2", "G2-3", "G2-4", "G2-5"]:
        assert r["checks"][k]["lulus"] is True, f"{k} harus lulus"
    assert r["checks"]["G2-6"]["catatan"] == "menunggu audit manual"


def test_gerbang_g2_gagal(tmp_path: Path):
    base, cand, emb = _setup_tree(tmp_path)

    _make_eval_json(base / "eval_bersarang_v3.json", emb, 0.70, "ml/data/splits_v3.json")
    _make_eval_json(cand / "eval_bersarang.json", emb, 0.66, "ml/data/splits_v5.json")

    y = np.array([0, 0, 1, 1, 2, 2])
    probs_base = np.array(
        [
            [0.9, 0.05, 0.03, 0.02],
            [0.8, 0.10, 0.05, 0.05],
            [0.1, 0.8, 0.05, 0.05],
            [0.1, 0.7, 0.1, 0.1],
            [0.1, 0.1, 0.7, 0.1],
            [0.1, 0.1, 0.8, 0.0],
        ]
    )
    probs_cand = np.array(
        [
            [0.2, 0.7, 0.05, 0.05],
            [0.2, 0.7, 0.05, 0.05],
            [0.1, 0.8, 0.05, 0.05],
            [0.2, 0.6, 0.1, 0.1],
            [0.6, 0.1, 0.2, 0.1],
            [0.55, 0.1, 0.25, 0.1],
        ]
    )
    _make_oof_npz(base / "oof_bersarang_v3.npz", probs_base, y)
    _make_oof_npz(cand / "oof_bersarang.npz", probs_cand, y)

    _make_indep_json(base / "uji_independen_v3.json", 0.75)
    _make_indep_json(cand / "uji_independen.json", 0.69)

    _make_e2e_json(base / "e2e_v3.json", target_hits=8, target_total=10, other_hits=2, other_total=10)
    _make_e2e_json(cand / "e2e.json", target_hits=7, target_total=10, other_hits=4, other_total=10)

    r = hitung_g2(base, cand)
    assert r["lulus"] is False
    assert r["checks"]["G2-1"]["lulus"] is False
    assert r["checks"]["G2-2"]["lulus"] is False
    assert r["checks"]["G2-3"]["lulus"] is False
    assert r["checks"]["G2-4"]["lulus"] is False
    assert r["checks"]["G2-5"]["lulus"] is False
    assert r["checks"]["G2-6"]["lulus"] is False
    assert "TIDAK DINILAI" in r["checks"]["G2-6"]["catatan"]
