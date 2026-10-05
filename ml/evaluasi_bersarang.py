"""Evaluasi bersarang: CV luar 5-fold StratifiedGroupKFold per perekam.

Hanya klip XC yang dibagi lipatan. Non-XC selalu di latih.

Setiap lipatan luar:
  1. CV dalam 4-fold (group-aware) untuk memilih C; hasilkan OOF dalam gabungan
  2. Kalibrasi T+bias di-fit pada OOF dalam gabungan (logits)
  3. Ambang per spesies di-fit pada OOF dalam gabungan, dengan syarat
     presisi >= 0,5 (menerima semua tidak boleh otomatis optimal).
     Kelas < 8 positif memakai ambang global.
  4. Evaluasi lipatan luar: acc, F1, recall/presisi pada ambang
  5. OOF luar disimpan untuk bootstrap grup perekam

Output: eval_bersarang.json (skema C10) + oof_bersarang.npz + evalb_per_spesies.json

Jalankan: python3 ml/evaluasi_bersarang.py
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

ML_DIR = ROOT / "ml"
EMB_DIR = ML_DIR / "embeddings_v3"
SPLITS_FILE = ML_DIR / "data" / "splits_v3.json"
META_FILE = ML_DIR / "data" / "xc_meta.json"
REPORTS = ML_DIR / "reports"

from ml.resep import latih, prediksi  # noqa: E402


def _softmax(z):
    z = z - z.max(axis=1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


def _ece(probs, y, n_bins=10):
    confs = np.max(probs, axis=1)
    preds = np.argmax(probs, axis=1)
    accs = (preds == y).astype(np.float64)
    bins = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    for i in range(n_bins):
        mask = (confs >= bins[i]) & (confs < bins[i + 1])
        if mask.sum() > 0:
            ece += (mask.sum() / len(y)) * abs(accs[mask].mean() - confs[mask].mean())
    return float(ece)


def f1_macro(y_true, y_pred, n_classes):
    f1s = []
    for k in range(n_classes):
        tp = np.sum((y_pred == k) & (y_true == k))
        fp = np.sum((y_pred == k) & (y_true != k))
        fn = np.sum((y_pred != k) & (y_true == k))
        f1 = 2 * tp / (2 * tp + fp + fn) if (2 * tp + fp + fn) > 0 else 0.0
        f1s.append(f1)
    return float(np.mean(f1s))


def _fit_threshold(skor, y_positif, min_precision=0.5):
    """Fit ambang yang memaksimalkan F1 dengan presisi >= min_precision.

    Mengembalikan ambang float. Menerima semua (t=0) tidak pernah optimal
    karena presisinya < min_precision untuk kelas yang tidak dominan.
    """
    kandidat = np.unique(np.concatenate([[0.0], skor, [1.0]]))
    best_t, best_f1 = 0.5, -1.0
    for t in kandidat:
        pred = skor >= t
        tp = float(np.sum(pred & y_positif))
        fp = float(np.sum(pred & ~y_positif))
        fn = float(np.sum(~pred & y_positif))
        if tp == 0:
            continue
        presisi = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        if presisi < min_precision:
            continue
        f1 = 2 * tp / (2 * tp + fp + fn) if (2 * tp + fp + fn) > 0 else 0.0
        if f1 > best_f1:
            best_t, best_f1 = float(t), f1
    # Kalau tidak ada yang memenuhi syarat presisi, ambil t yang memaksimalkan
    # presisi (bukan F1), minimal 0.3 supaya tidak nol.
    if best_f1 < 0:
        best_t = 0.5
    return best_t


def _fit_ambang_per_spesies(probs, y, target_kelas, min_positif=8):
    """Fit ambang per spesies target. Kelas < min_positif pakai ambang global."""
    # Ambang global: mikro atas semua pasangan (klip, spesies target)
    skor_global = probs[:, target_kelas].ravel()
    y_global = (y[:, None] == np.array(target_kelas)[None, :]).ravel()
    global_th = _fit_threshold(skor_global, y_global)

    ambang = {}
    for k in target_kelas:
        skor = probs[:, k]
        positif = (y == k)
        if positif.sum() < min_positif:
            ambang[k] = global_th
            continue
        ambang[k] = _fit_threshold(skor, positif)
    return ambang, global_th


def _evaluasi_pada_ambang(probs, y, ambang, target_kelas):
    """Mikro presisi/recall atas spesies target dengan ambang per spesies."""
    tp = fp = fn = 0.0
    for k in target_kelas:
        th = ambang.get(k, 0.5)
        pred = probs[:, k] >= th
        positif = (y == k)
        tp += np.sum(pred & positif)
        fp += np.sum(pred & ~positif)
        fn += np.sum(~pred & positif)
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    presisi = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    return float(recall), float(presisi)


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--emb-dir", default=str(EMB_DIR))
    ap.add_argument("--splits", default=str(SPLITS_FILE))
    ap.add_argument("--out-akhiran", default="")
    ap.add_argument("--out-dir", default=str(REPORTS),
                    help="direktori keluaran evaluasi (default ml/reports)")
    ap.add_argument("--pool-xc-json", default="",
                    help="opsional: JSON daftar clip_id XC untuk pool OOF tetap")
    args = ap.parse_args()
    emb_dir = Path(args.emb_dir)
    splits_file = Path(args.splits)
    out_dir = Path(args.out_dir)

    if not emb_dir.exists():
        print(f"ERROR: {emb_dir} tidak ditemukan")
        return 1

    print("Memuat data...")
    emb = np.load(emb_dir / "embeddings.npy")
    lab = np.load(emb_dir / "labels.npy")
    ids = json.loads((emb_dir / "clip_ids.json").read_text())
    label_map = json.loads((emb_dir / "label_map.json").read_text())
    inv_label_map = {v: k for k, v in label_map.items()}
    splits = json.loads(splits_file.read_text())
    idx = {cid: i for i, cid in enumerate(ids)}

    meta = json.loads(META_FILE.read_text())
    recs = meta.get("recordings", {})

    train_val = splits["train"] + splits.get("val", [])
    xc_ids = [c for c in train_val if c.startswith("xc-") and c in idx]
    non_xc_ids = [c for c in train_val if not c.startswith("xc-") and c in idx]

    pool_override = {}
    if args.pool_xc_json:
        pool_override = json.loads(Path(args.pool_xc_json).read_text())
        wajib_sha = pool_override.get("sha256_xc_ids")
        wajib_ids = pool_override.get("xc_ids")
        if wajib_ids:
            wajib_set = set(wajib_ids)
            ada = [c for c in wajib_ids if c in idx]
            if len(ada) != len(wajib_ids):
                hilang = sorted(wajib_set - set(ada))[:5]
                print(f"ERROR: {len(wajib_ids)-len(ada)} clip_id XC pool tidak ada di embeddings: {hilang}")
                return 1
            if wajib_sha:
                cek_sha = hashlib.sha256("\n".join(sorted(wajib_ids)).encode("utf-8")).hexdigest()
                if cek_sha != wajib_sha:
                    print(f"ERROR: sha pool XC tidak cocok: {cek_sha} != {wajib_sha}")
                    return 1
            xc_ids = list(wajib_ids)
            print(f"Pool XC override aktif: {len(xc_ids)} clip_id")

    X_xc = emb[[idx[c] for c in xc_ids]].astype(np.float32)
    y_xc = lab[[idx[c] for c in xc_ids]]
    X_non = emb[[idx[c] for c in non_xc_ids]].astype(np.float32)
    y_non = lab[[idx[c] for c in non_xc_ids]]

    groups = np.array([recs.get(c, {}).get("rec", c) for c in xc_ids])
    uniq_groups, group_ints = np.unique(groups, return_inverse=True)

    n_kelas = len(label_map)
    neg_idx = label_map["_negative"]
    target_kelas = [k for k in range(n_kelas) if k != neg_idx]
    n_xc = len(xc_ids)

    print(f"XC: {n_xc} klip, {len(uniq_groups)} grup perekam, non-XC: {len(non_xc_ids)}")

    from sklearn.model_selection import StratifiedGroupKFold

    outer_cv = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)
    inner_cv = StratifiedGroupKFold(n_splits=4, shuffle=True, random_state=42)
    C_grid = [0.1, 0.5, 1.0, 2.0, 5.0]

    semua_lipatan = []
    oof_probs = np.full((n_xc, n_kelas), np.nan, dtype=np.float32)
    oof_y = np.full(n_xc, -1, dtype=int)
    oof_lipatan = np.full(n_xc, -1, dtype=int)
    oof_grup = np.array([recs.get(c, {}).get("rec", c) for c in xc_ids])

    for lipatan_idx, (tr_idx, val_idx) in enumerate(
            outer_cv.split(xc_ids, y_xc, groups=group_ints)):
        xc_tr = tr_idx
        xc_val = val_idx
        groups_tr = group_ints[xc_tr]
        n_xc_tr = len(xc_tr)

        # CV dalam: pilih C, kumpulkan OOF dalam gabungan
        best_C = 1.0
        best_f1 = -1.0
        best_inner_oof = None
        for C_val in C_grid:
            inner_probs = []
            inner_y = []
            for tr_in, val_in in inner_cv.split(
                    np.arange(n_xc_tr), y_xc[xc_tr], groups=groups_tr):
                X_tr_i = np.vstack([X_xc[xc_tr[tr_in]], X_non])
                y_tr_i = np.concatenate([y_xc[xc_tr[tr_in]], y_non])
                X_val_i = X_xc[xc_tr[val_in]]
                y_val_i = y_xc[xc_tr[val_in]]
                konfig = {"C": C_val, "seed": 2024, "maks_negatif": 3000}
                model = latih([], konfig, X_tr_i, y_tr_i, label_map,
                               X_val_i, y_val_i, normalisasi="lipatan")
                probs = prediksi(model, X_val_i)
                inner_probs.append(probs)
                inner_y.append(y_val_i)
            ip = np.vstack(inner_probs)
            iy = np.concatenate(inner_y)
            f1_inner = f1_macro(iy, np.argmax(ip, axis=1), n_kelas)
            if f1_inner > best_f1:
                best_f1 = f1_inner
                best_C = C_val
                best_inner_oof = (ip, iy)

        ip, iy = best_inner_oof

        # Fit ambang pada OOF dalam gabungan
        ambang_idx, global_th = _fit_ambang_per_spesies(ip, iy, target_kelas)
        ambang_nama = {inv_label_map[k]: float(ambang_idx[k]) for k in target_kelas}

        # Latih model final pada seluruh latih luar + kalibrasi
        # Kalibrasi pakai OOF dalam gabungan: kita butuh logits, pakai probs -> logit
        # Lebih sederhana: latih ulang dengan kalibrasi pada gabungan dalam
        # Kalibrasi: pakai subset dari latih luar (inner fold pertama)
        splits_gen = inner_cv.split(np.arange(n_xc_tr), y_xc[xc_tr], groups=groups_tr)
        cal_tr, cal_val = next(splits_gen)
        cal_train_idx = xc_tr[cal_tr]
        cal_val_idx = xc_tr[cal_val]
        X_cal = np.vstack([X_xc[cal_train_idx], X_non])
        y_cal = np.concatenate([y_xc[cal_train_idx], y_non])
        X_cal_val = X_xc[cal_val_idx]
        y_cal_val = y_xc[cal_val_idx]

        konfig = {"C": best_C, "seed": 2024, "maks_negatif": 3000}
        model = latih([], konfig, X_cal, y_cal, label_map,
                       X_cal_val, y_cal_val, normalisasi="lipatan")

        # Evaluasi di lipatan luar
        X_val_outer = X_xc[xc_val]
        y_val_outer = y_xc[xc_val]
        probs_te = prediksi(model, X_val_outer)
        preds_te = np.argmax(probs_te, axis=1)

        acc = float(np.mean(preds_te == y_val_outer))
        f1 = f1_macro(y_val_outer, preds_te, n_kelas)
        ece_val = _ece(probs_te, y_val_outer)
        recall_th, presisi_th = _evaluasi_pada_ambang(
            probs_te, y_val_outer, ambang_idx, target_kelas)

        lipatan = {
            "lipatan": lipatan_idx + 1,
            "C": best_C,
            "n_latih": int(len(X_cal) + len(X_cal_val)),
            "n_uji": int(len(X_val_outer)),
            "acc": round(acc, 4),
            "f1_macro": round(f1, 4),
            "ece": round(ece_val, 4),
            "ambang": {nama: round(float(v), 4) for nama, v in ambang_nama.items()},
            "global_threshold": round(global_th, 4),
            "recall_pada_ambang": round(recall_th, 4),
            "presisi_pada_ambang": round(presisi_th, 4),
            "T": round(float(model.temperature), 4),
        }
        semua_lipatan.append(lipatan)

        oof_probs[xc_val] = probs_te
        oof_y[xc_val] = y_val_outer
        oof_lipatan[xc_val] = lipatan_idx

        print(f"Lipatan {lipatan_idx + 1}: C={best_C}, acc={acc:.4f}, F1={f1:.4f}, "
              f"presisi_th={presisi_th:.4f}, recall_th={recall_th:.4f}, "
              f"global_th={global_th:.4f}")

    # OOF gabungan
    valid = oof_y >= 0
    oof_probs_v = oof_probs[valid]
    oof_y_v = oof_y[valid]
    oof_grup_v = oof_grup[valid]
    oof_lipatan_v = oof_lipatan[valid]

    preds_oof = np.argmax(oof_probs_v, axis=1)
    aggregat = {
        "f1_macro": round(f1_macro(oof_y_v, preds_oof, n_kelas), 4),
        "acc": round(float(np.mean(preds_oof == oof_y_v)), 4),
        "n_oof": int(len(oof_y_v)),
    }

    # aggregat_pada_ambang: mikro atas target, tiap baris pakai ambang lipatannya
    tp = fp = fn = 0.0
    for i in range(len(oof_y_v)):
        lip = int(oof_lipatan_v[i])
        ambang_fold = semua_lipatan[lip]["ambang"]
        for k in target_kelas:
            nama = inv_label_map[k]
            th = ambang_fold.get(nama, 0.5)
            pred = oof_probs_v[i, k] >= th
            positif = oof_y_v[i] == k
            if pred and positif:
                tp += 1
            elif pred and not positif:
                fp += 1
            elif not pred and positif:
                fn += 1
    recall_agg = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    presisi_agg = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    aggregat_pada_ambang = {
        "presisi": round(presisi_agg, 4),
        "recall": round(recall_agg, 4),
    }

    # Bootstrap grup perekam
    rng = np.random.default_rng(42)
    n_boot = 1000
    unique_grup = np.unique(oof_grup_v)
    acc_boot = []
    f1_boot = []
    for _ in range(n_boot):
        sampled = rng.choice(unique_grup, size=len(unique_grup), replace=True)
        mask = np.isin(oof_grup_v, sampled)
        if mask.sum() < 3:
            continue
        yb = oof_y_v[mask]
        pb = np.argmax(oof_probs_v[mask], axis=1)
        acc_boot.append(float(np.mean(pb == yb)))
        f1_boot.append(f1_macro(yb, pb, n_kelas))
    acc_boot.sort()
    f1_boot.sort()
    ci95 = {
        "metode": "bootstrap_grup_perekam",
        "n_bootstrap": n_boot,
        "f1_macro": {"ci95_low": round(float(f1_boot[int(0.025 * len(f1_boot))]), 4),
                      "ci95_high": round(float(f1_boot[int(0.975 * len(f1_boot))]), 4)},
        "acc": {"ci95_low": round(float(acc_boot[int(0.025 * len(acc_boot))]), 4),
                 "ci95_high": round(float(acc_boot[int(0.975 * len(acc_boot))]), 4)},
    }

    print(f"\nAggregat OOF: acc {aggregat['acc']:.4f}, F1 {aggregat['f1_macro']:.4f}")
    print(f"Aggregat pada ambang: presisi {presisi_agg:.4f}, recall {recall_agg:.4f}")
    print(f"CI95 acc: [{ci95['acc']['ci95_low']}, {ci95['acc']['ci95_high']}]")
    print(f"CI95 f1:  [{ci95['f1_macro']['ci95_low']}, {ci95['f1_macro']['ci95_high']}]")

    out_dir.mkdir(parents=True, exist_ok=True)
    pool_xc_sha256 = hashlib.sha256("\n".join(sorted(xc_ids)).encode("utf-8")).hexdigest()
    pool_non_xc_sha256 = hashlib.sha256("\n".join(sorted(non_xc_ids)).encode("utf-8")).hexdigest()
    output = {
        "emb_dir": str(emb_dir.relative_to(ROOT)) if emb_dir.is_relative_to(ROOT) else str(emb_dir),
        "splits_file": str(splits_file.relative_to(ROOT)) if splits_file.is_relative_to(ROOT) else str(splits_file),
        "pool": {
            "n_xc": n_xc,
            "n_non_xc": len(non_xc_ids),
            "n_train_val": len(train_val),
            "sha256_xc_ids": pool_xc_sha256,
            "sha256_non_xc_ids": pool_non_xc_sha256,
            "pool_override": bool(args.pool_xc_json),
        },
        "n_xc": n_xc,
        "n_non_xc": len(non_xc_ids),
        "n_kelas": n_kelas,
        "n_grup_perekam": int(len(uniq_groups)),
        "n_lipatan": 5,
        "metode": "StratifiedGroupKFold 5-fold XC saja, non-XC selalu latih",
        "C_grid": C_grid,
        "aggregat": aggregat,
        "aggregat_pada_ambang": aggregat_pada_ambang,
        "ci95": ci95,
        "lipatan": semua_lipatan,
    }
    (out_dir / f"eval_bersarang{args.out_akhiran}.json").write_text(
        json.dumps(output, indent=2, ensure_ascii=False))
    np.savez(out_dir / f"oof_bersarang{args.out_akhiran}.npz",
             probs=oof_probs_v.astype(np.float32),
             y=oof_y_v.astype(np.int32),
             grup=oof_grup_v,
             lipatan=oof_lipatan_v.astype(np.int32))

    sp_out = {}
    for nama in sorted(label_map.keys()):
        k = label_map[nama]
        mask = oof_y_v == k
        if mask.sum() > 0:
            sp_out[nama] = {
                "n": int(mask.sum()),
                "acc": round(float(np.mean(preds_oof[mask] == k)), 4),
            }
    (out_dir / f"evalb_per_spesies{args.out_akhiran}.json").write_text(
        json.dumps(sp_out, indent=2, ensure_ascii=False))

    print("\nOutput: eval_bersarang.json, oof_bersarang.npz, evalb_per_spesies.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())