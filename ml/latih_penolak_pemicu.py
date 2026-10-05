"""Latih regresi logistik untuk menolak 8 spesies pemicu (S4, ML_09).

Pemicu dari ml/reports/pemicu_palsu.md: suara spesies kerabat dekat target
yang membuat model salah menuduh. S4 memisahkan mereka jadi kelas sendiri
lewat classifier biner per spesies (one-vs-rest regresi logistik di atas
embedding BirdNET 1024-dim), BUKAN menambah kelas baru ke MLP utama (itu
butuh retrain penuh dan berisiko turunkan F1 kelas target).

Pipeline:
1. Baca embedding pemicu (dari ml/embeddings_pemicu/, hasil extract_embeddings.py
   terhadap ml/data/manifest_pemicu_xc.csv)
2. Baca embedding negatif umum (ml/embeddings_negatif_xc/) sebagai kontras
3. Latih 8 classifier biner (satu per spesies pemicu): pemicu vs bukan-pemicu
4. Simpan koefisien ke ml/checkpoints_pemicu/pemicu_lr.npz
5. Evaluasi di luar bagian pilih/lapor supaya tidak bocor ke metrik gerbang

Dipanggil dari cascade.py: kalau segmen Track B diprediksi masuk salah satu
8 kelas pemicu dengan confidence tinggi, deteksi target di segmen itu DIBUANG
(bukan dilaporkan sebagai target), bukan ditambah sebagai kelas baru.

Jalankan:
  source .venv/bin/activate && python ml/latih_penolak_pemicu.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score

ROOT = Path(__file__).resolve().parent.parent
ML_DIR = ROOT / "ml"
EMB_PEMICU_DIR = ML_DIR / "embeddings_pemicu"
EMB_NEGATIF_DIR = ML_DIR / "embeddings_negatif_xc"
CKPT_DIR = ML_DIR / "checkpoints_pemicu"
REPORTS = ML_DIR / "reports"

SPESIES_PEMICU = [
    "Orthotomus_ruficeps",
    "Accipiter_badius",
    "Dicaeum_trochileum",
    "Aethopyga_mystacalis",
    "Hemipus_hirundinaceus",
    "Merops_viridis",
    "Centropus_sinensis",
    "Dendrocygna_arcuata",
]


def muat_embedding(emb_dir: Path):
    """Baca embeddings.npy, labels.npy, label_map.json dari satu folder."""
    emb = np.load(emb_dir / "embeddings.npy")
    labels = np.load(emb_dir / "labels.npy")
    label_map = json.loads((emb_dir / "label_map.json").read_text())
    inv_map = {v: k for k, v in label_map.items()}
    return emb, labels, label_map, inv_map


def main() -> int:
    if not EMB_PEMICU_DIR.exists():
        print(f"ERROR: {EMB_PEMICU_DIR} tidak ada. Jalankan dulu:")
        print(f"  python ml/data/extract_embeddings.py --manifest ml/data/manifest_pemicu_xc.csv "
              f"--out-dir {EMB_PEMICU_DIR} --ckpt-dir {CKPT_DIR}")
        return 1
    if not EMB_NEGATIF_DIR.exists():
        print(f"ERROR: {EMB_NEGATIF_DIR} tidak ada (dibutuhkan sebagai kontras negatif)")
        return 1

    emb_p, lab_p, map_p, inv_p = muat_embedding(EMB_PEMICU_DIR)
    emb_n, lab_n, map_n, inv_n = muat_embedding(EMB_NEGATIF_DIR)

    print(f"Embedding pemicu: {emb_p.shape}, spesies: {list(map_p.keys())}")
    print(f"Embedding negatif kontras: {emb_n.shape}")

    hasil_cv = {}
    model_per_spesies = {}

    CKPT_DIR.mkdir(parents=True, exist_ok=True)

    for spesies in SPESIES_PEMICU:
        if spesies not in map_p:
            print(f"  [{spesies}] SKIP: tidak ada embedding (klip gagal unduh?)")
            hasil_cv[spesies] = {"status": "tidak_ada_data"}
            continue

        idx_pos = lab_p == map_p[spesies]
        n_pos = int(idx_pos.sum())
        if n_pos < 5:
            print(f"  [{spesies}] SKIP: hanya {n_pos} klip, kurang dari 5")
            hasil_cv[spesies] = {"status": "data_kurang", "n_pos": n_pos}
            continue

        X_pos = emb_p[idx_pos]
        y_pos = np.ones(n_pos)

        # Kontras: embedding spesies pemicu LAIN + sampel negatif umum
        idx_pemicu_lain = ~idx_pos
        X_neg_pemicu = emb_p[idx_pemicu_lain]
        rng = np.random.default_rng(2026)
        n_neg_umum = min(len(emb_n), n_pos * 4)
        idx_neg_umum = rng.choice(len(emb_n), size=n_neg_umum, replace=False)
        X_neg_umum = emb_n[idx_neg_umum]

        X_neg = np.vstack([X_neg_pemicu, X_neg_umum]) if len(X_neg_pemicu) > 0 else X_neg_umum
        y_neg = np.zeros(len(X_neg))

        X = np.vstack([X_pos, X_neg])
        y = np.concatenate([y_pos, y_neg])

        clf = LogisticRegression(
            max_iter=2000, class_weight="balanced", C=1.0, random_state=2026,
        )

        n_splits = min(5, n_pos)
        if n_splits < 2:
            clf.fit(X, y)
            cv_scores = np.array([np.nan])
        else:
            skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=2026)
            cv_scores = cross_val_score(clf, X, y, cv=skf, scoring="f1")
            clf.fit(X, y)

        model_per_spesies[spesies] = {
            "coef": clf.coef_[0].tolist(),
            "intercept": float(clf.intercept_[0]),
        }

        hasil_cv[spesies] = {
            "status": "ok",
            "n_pos": n_pos,
            "n_neg": len(X_neg),
            "f1_cv_mean": float(np.nanmean(cv_scores)),
            "f1_cv_std": float(np.nanstd(cv_scores)) if len(cv_scores) > 1 else 0.0,
        }
        print(f"  [{spesies}] n_pos={n_pos} n_neg={len(X_neg)} "
              f"F1_cv={hasil_cv[spesies]['f1_cv_mean']:.3f}")

    # Simpan model
    out_path = CKPT_DIR / "pemicu_lr.npz"
    np.savez(
        out_path,
        **{f"{sp}__coef": np.array(m["coef"]) for sp, m in model_per_spesies.items()},
        **{f"{sp}__intercept": np.array([m["intercept"]]) for sp, m in model_per_spesies.items()},
    )
    (CKPT_DIR / "pemicu_species.json").write_text(
        json.dumps(list(model_per_spesies.keys()), indent=2)
    )

    report_path = REPORTS / "latih_penolak_pemicu.json"
    report_path.write_text(json.dumps({
        "spesies_pemicu_target": SPESIES_PEMICU,
        "hasil_per_spesies": hasil_cv,
        "n_model_terlatih": len(model_per_spesies),
    }, indent=2, ensure_ascii=False))

    print(f"\nModel tersimpan: {out_path}")
    print(f"Report: {report_path}")
    print(f"Model terlatih: {len(model_per_spesies)}/{len(SPESIES_PEMICU)} spesies")

    return 0


if __name__ == "__main__":
    sys.exit(main())
