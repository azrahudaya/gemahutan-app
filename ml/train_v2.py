"""Latih classifier GemaHutan pada korpus versi 2.

Skrip ini memakai ulang mesin latih yang sudah terbukti di `ml/train.py`
(kelas `MLP`, `train_one`, `load_data`, kalibrasi vector scaling) tetapi
mengarahkan seluruh berkas masukan dan keluaran ke korpus v2, sehingga model
produksi di `ml/checkpoints/` tidak tersentuh.

Korpus v2 sengaja memakai split lama apa adanya supaya angka uji bisa
dibandingkan langsung dengan baseline 0,6772. Seluruh data eksternal berada di
train, jadi kenaikan angka berasal dari data latih, bukan dari perubahan uji.

Contoh:
    python3 ml/train_v2.py \
        --emb-dir ml/embeddings_v2 \
        --splits ml/data/splits_v2.json \
        --out-dir ml/checkpoints_v2 \
        --report-dir ml/reports_v2
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

import numpy as np

ML_DIR = Path(__file__).resolve().parent
if str(ML_DIR.parent) not in sys.path:
    sys.path.insert(0, str(ML_DIR.parent))

from ml.train import (  # noqa: E402
    accuracy,
    load_data,
    save_history_plot,
    train_one,
)


def metrik_per_kelas(y_true: np.ndarray, y_pred: np.ndarray, label_map: dict) -> list[dict]:
    """Hitung precision, recall, dan support per kelas."""
    inv = {v: k for k, v in label_map.items()}
    hasil = []
    for idx in sorted(inv):
        nama = inv[idx]
        tp = int(np.sum((y_pred == idx) & (y_true == idx)))
        fp = int(np.sum((y_pred == idx) & (y_true != idx)))
        fn = int(np.sum((y_pred != idx) & (y_true == idx)))
        support = int(np.sum(y_true == idx))
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
        hasil.append(
            {
                "kelas": nama,
                "precision": round(prec, 4),
                "recall": round(rec, 4),
                "f1": round(f1, 4),
                "support": support,
            }
        )
    return hasil


def hitung_bobot_kelas(
    y_train: np.ndarray,
    num_classes: int,
    mode: str,
) -> tuple[np.ndarray, dict]:
    """Hitung bobot kelas dengan beberapa mode.

    Korpus v2 punya rasio kelas 701 kali (`_negative` 5612 klip melawan
    `Gallus gallus` 8 klip). Bobot `balanced` biasa memberi `_negative` bobot
    0,055 sehingga kelas negatif praktis tidak dilatih, dan kelas kecil diberi
    bobot 38 sehingga mendominasi. Mode lain disediakan untuk mengatasinya.

    mode:
      balanced   -- 1/n, seperti sebelumnya
      sqrt       -- 1/sqrt(n), rasio jadi sekitar 26 kali, bukan 701
      capped:N   -- balanced dipotong di N
      none       -- semua 1
    """
    n = np.bincount(y_train, minlength=num_classes).astype(np.float64)
    n = np.maximum(n, 1)

    if mode == "none":
        w = np.ones(num_classes, dtype=np.float64)
    elif mode == "sqrt":
        w = 1.0 / np.sqrt(n)
        w = w / w.mean()
    elif mode.startswith("capped"):
        batas = float(mode.split(":")[1]) if ":" in mode else 10.0
        w = len(y_train) / (num_classes * n)
        w = np.minimum(w, batas)
    else:
        w = len(y_train) / (num_classes * n)

    return w.astype(np.float32), {
        "mode": mode,
        "rasio_maks_min": float(w.max() / max(w.min(), 1e-12)),
    }


def batasi_negatif(
    X_train: np.ndarray,
    y_train: np.ndarray,
    indeks_negatif: int,
    maks: int,
    seed: int,
) -> tuple[np.ndarray, np.ndarray, dict]:
    """Turunkan jumlah klip `_negative` di train ke angka maksimum.

    Dipakai kalau rasio negatif terhadap kelas positif terlalu ekstrem sehingga
    pembobotan apa pun tetap berat sebelah. Pengambilan sampel dilakukan acak
    dengan seed tetap supaya hasilnya bisa diulang.
    """
    pos = y_train != indeks_negatif
    neg_idx = np.flatnonzero(~pos)
    if maks <= 0 or len(neg_idx) <= maks:
        return X_train, y_train, {"dipakai": int(len(neg_idx)), "dibuang": 0}

    rng = np.random.default_rng(seed)
    ambil = rng.choice(neg_idx, size=maks, replace=False)
    simpan = np.concatenate([np.flatnonzero(pos), np.sort(ambil)])
    rng.shuffle(simpan)
    return X_train[simpan], y_train[simpan], {
        "dipakai": int(maks),
        "dibuang": int(len(neg_idx) - maks),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Latih classifier GemaHutan korpus v2")
    parser.add_argument("--emb-dir", default=str(ML_DIR / "embeddings_v2"))
    parser.add_argument("--splits", default=str(ML_DIR / "data" / "splits_v2.json"))
    parser.add_argument("--out-dir", default=str(ML_DIR / "checkpoints_v2"))
    parser.add_argument("--report-dir", default=str(ML_DIR / "reports_v2"))
    parser.add_argument("--epochs", type=int, default=300)
    parser.add_argument("--hidden", type=int, default=256)
    parser.add_argument("--lr", type=float, default=0.001)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--seed", type=int, default=2024)
    parser.add_argument("--limit", type=int, default=0, help="Batasi jumlah klip train untuk uji cepat")
    parser.add_argument(
        "--class-weight",
        default="balanced",
        help="balanced | sqrt | capped:N | none",
    )
    parser.add_argument(
        "--maks-negatif",
        type=int,
        default=0,
        help="Batasi jumlah klip _negative di train. 0 berarti pakai semua.",
    )
    args = parser.parse_args()

    np.random.seed(args.seed)

    out_dir = Path(args.out_dir)
    report_dir = Path(args.report_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)

    print("Memuat data dari", args.emb_dir)
    X_train, y_train, X_val, y_val, X_test, y_test, label_map, mean, std = load_data(
        emb_dir=Path(args.emb_dir), splits_file=Path(args.splits)
    )

    if args.limit:
        X_train, y_train = X_train[: args.limit], y_train[: args.limit]

    num_classes = len(label_map)
    input_dim = X_train.shape[1]
    inv_map = {v: k for k, v in label_map.items()}
    idx_negatif = label_map.get("_negative", -1)

    print(f"Train: {len(X_train)}  Val: {len(X_val)}  Test: {len(X_test)}")
    print(f"Input dim: {input_dim}  Kelas: {num_classes}")

    potong_info: dict = {"dipakai": int(np.sum(y_train == idx_negatif)), "dibuang": 0}
    if args.maks_negatif and idx_negatif >= 0:
        X_train, y_train, potong_info = batasi_negatif(
            X_train, y_train, idx_negatif, args.maks_negatif, args.seed
        )
        print(f"Negatif dipotong: {potong_info}")

    bobot, info_bobot = hitung_bobot_kelas(y_train, num_classes, args.class_weight)
    print(f"Bobot kelas mode: {info_bobot['mode']}, rasio maks/min = {info_bobot['rasio_maks_min']:.1f}")
    print("Sebaran train:", dict(Counter(inv_map[int(k)] for k in y_train)))

    print(f"\nMelatih {args.epochs} epoch...")
    hasil = train_one(
        X_train, y_train, X_val, y_val, X_test, y_test,
        num_classes, input_dim, args, out_dir, class_weights=bobot,
    )

    model = hasil["model"]
    model.training = False
    pred_test = model.predict(X_test)
    acc_raw = accuracy(pred_test, y_test)

    print(f"\nAkurasi uji          : {hasil['test_acc']:.4f}")
    print(f"Akurasi uji mentah   : {acc_raw:.4f}")
    print(f"F1 makro             : {hasil['f1_macro']:.4f}")
    print(f"Best val acc         : {hasil['best_val_acc']:.4f} (epoch {hasil['best_epoch'] + 1})")
    print(f"Kalibrasi T          : {hasil['temperature']:.4f}")
    print(f"NLL {hasil['nll_before']:.4f} ke {hasil['nll_after']:.4f} ({hasil['nll_improvement_pct']:.2f} persen)")

    label_map_str = {str(k): v for k, v in label_map.items()}

    model.save(
        str(out_dir / "best_model.npz"),
        temperature=hasil["temperature"],
        bias=hasil["bias"],
    )
    np.savez(out_dir / "normalization.npz", mean=mean, std=std)

    temp_json = {
        "method": "vector_scaling_T+b",
        "temperature": float(hasil["temperature"]),
        "bias": [float(b) for b in hasil["bias"]],
        "nll_before": hasil["nll_before"],
        "nll_after": hasil["nll_after"],
        "nll_improvement_pct": hasil["nll_improvement_pct"],
        "val_samples": int(len(y_val)),
        "num_classes": num_classes,
        "label_map": label_map_str,
        "bundled_in_best_model": True,
    }
    (out_dir / "temperature.json").write_text(json.dumps(temp_json, indent=2))

    meta = {
        "epoch": int(hasil["best_epoch"]) + 1,
        "best_val_acc": hasil["best_val_acc"],
        "test_acc": hasil["test_acc"],
        "test_acc_raw": acc_raw,
        "f1_macro": hasil["f1_macro"],
        "seed": args.seed,
        "n_train": int(len(X_train)),
        "n_val": int(len(y_val)),
        "n_test": int(len(y_test)),
        "korpus": "v2",
        "dibuat": datetime.now().isoformat(timespec="seconds"),
    }
    (out_dir / "meta.json").write_text(json.dumps(meta, indent=2))

    per_kelas = metrik_per_kelas(y_test, pred_test, label_map)
    (report_dir / "metrik_per_kelas.json").write_text(
        json.dumps(per_kelas, indent=2, ensure_ascii=False)
    )
    (report_dir / "riwayat.json").write_text(
        json.dumps(hasil["history"], indent=2, ensure_ascii=False)
    )
    (report_dir / "metrics.json").write_text(
        json.dumps(
            {
                "test_acc": hasil["test_acc"],
                "test_acc_raw": acc_raw,
                "val_acc": hasil["best_val_acc"],
                "macro_f1": hasil["f1_macro"],
                "per_species": per_kelas,
            },
            indent=2,
            ensure_ascii=False,
        )
    )

    try:
        save_history_plot(
            hasil["history"],
            report_dir / "training_history.png",
            title=f"Korpus v2 seed={args.seed} val_acc={hasil['best_val_acc']:.4f}",
        )
    except Exception as exc:
        print("plot dilewati:", exc)

    print("\nKelas paling lemah (recall terendah):")
    for r in sorted(per_kelas, key=lambda x: x["recall"])[:8]:
        print(f"   {r['kelas']:32s} recall={r['recall']:.3f} f1={r['f1']:.3f} support={r['support']}")

    print("\nArtefak:")
    print("  ", out_dir / "best_model.npz")
    print("  ", out_dir / "normalization.npz")
    print("  ", out_dir / "temperature.json")
    print("  ", out_dir / "meta.json")
    print("  ", report_dir / "metrics.json")


if __name__ == "__main__":
    main()
