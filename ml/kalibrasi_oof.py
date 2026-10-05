"""Kalibrasi ambang dan suhu dari OOF (bukan split val 127 klip).

Semua pemilihan parameter dilakukan pada prediksi out-of-fold CV berkelompok.
Kelas dengan < 8 positif OOF memakai ambang global.
Laporkan ECE OOF dan dampak di uji independen.
"""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

ML_DIR = ROOT / "ml"
OOF_DIR = ML_DIR / "reports" / "oof"
OUT_THRESHOLDS = ML_DIR / "reports" / "thresholds.json"
OUT_OOF_META = ML_DIR / "reports" / "kandidat" / "thresholds_oof.json"
EVAL_GRUP = ML_DIR / "reports" / "eval_grup.json"
EMB_DIR = ML_DIR / "embeddings_v3"

MIN_POSITIF_OOF = 8


def softmax(z):
    z = z - z.max(axis=1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


def nll(probs, y):
    return float(np.mean(-np.log(probs[np.arange(len(y)), y] + 1e-9)))


def ece(probs, y_true, n_bins=10):
    confs = np.max(probs, axis=1)
    preds = np.argmax(probs, axis=1)
    correct = (preds == y_true).astype(np.float64)
    bins = np.linspace(0, 1, n_bins + 1)
    ece_sum = 0.0
    for i in range(n_bins):
        mask = (confs >= bins[i]) & (confs < bins[i + 1])
        if mask.sum() > 0:
            ece_sum += mask.sum() * abs(correct[mask].mean() - confs[mask].mean())
    return float(ece_sum / len(y_true))


def temperature_scale(logits, y, steps=2000, lr=0.1):
    """Optimasi T dari logits OOF."""
    best_T, best_nll = 1.0, float("inf")
    for T_cand in np.arange(0.05, 5.0, 0.005):
        val = nll(softmax(logits / T_cand), y)
        if val < best_nll:
            best_T, best_nll = float(T_cand), val
    return best_T, best_nll


def bias_scale(logits, y, T, steps=2000, lr=0.05):
    """Bias aditif per kelas dari logits OOF."""
    n_kelas = logits.shape[1]
    bias = np.zeros(n_kelas, dtype=np.float32)
    satu_panas = np.zeros((len(y), n_kelas), dtype=np.float32)
    satu_panas[np.arange(len(y)), y] = 1.0
    for _ in range(steps):
        probs = softmax((logits + bias) / T)
        grad = ((probs - satu_panas).mean(axis=0)).astype(np.float32)
        bias -= lr * grad
    return bias


def find_per_species_thresholds(probs, y, label_map, min_positif=MIN_POSITIF_OOF):
    """Cari ambang F1-optimal per kelas dari OOF probs."""
    n_kelas = probs.shape[1]
    inv = {v: k for k, v in label_map.items()}
    thresholds = {}

    # Ambang global untuk kelas dengan sedikit sampel
    global_best, global_best_f1 = 0.3, -1.0
    for t in np.arange(0.05, 0.95, 0.01):
        tp = fp = fn = 0
        for c in range(n_kelas):
            skor = probs[:, c]
            positif = y == c
            if positif.sum() == 0:
                continue
            pred = skor >= t
            tp += np.sum(pred & positif)
            fp += np.sum(pred & ~positif)
            fn += np.sum(~pred & positif)
        f1 = 2 * tp / (2 * tp + fp + fn) if (2 * tp + fp + fn) else 0.0
        if f1 > global_best_f1:
            global_best, global_best_f1 = float(t), f1

    for c in range(n_kelas):
        nama = inv.get(c, str(c))
        skor = probs[:, c]
        positif = y == c
        n_pos = int(positif.sum())

        if n_pos < min_positif:
            thresholds[nama] = global_best
            continue

        kandidat = np.unique(np.concatenate([skor, [0.0, 1.0]]))
        terbaik, f1_terbaik = global_best, -1.0
        for t in kandidat:
            pred = skor >= t
            if pred.sum() == 0:
                continue
            tp = np.sum(pred & positif)
            fp = np.sum(pred & ~positif)
            fn = np.sum(~pred & positif)
            f1 = 2 * tp / (2 * tp + fp + fn) if (2 * tp + fp + fn) else 0.0
            if f1 > f1_terbaik:
                terbaik, f1_terbaik = float(t), f1
        thresholds[nama] = terbaik

    return thresholds, global_best


def main():
    # Load OOF data
    oof_data = np.load(OOF_DIR / "oof_probs.npz")
    probs_oof = oof_data["probs"]
    y_oof = oof_data["labels"]
    print(f"Loaded OOF: {probs_oof.shape[0]} clips, {probs_oof.shape[1]} classes")

    # Load label map
    label_map = json.loads((EMB_DIR / "label_map.json").read_text())

    # 1. Temperature + bias dari OOF
    eps = 1e-9
    logits = np.log(np.clip(probs_oof, eps, 1.0))
    nll_before = nll(probs_oof, y_oof)

    T, _ = temperature_scale(logits, y_oof)
    bias = bias_scale(logits, y_oof, T)

    probs_cal = softmax((logits + bias) / T)
    nll_after = nll(probs_cal, y_oof)
    ece_before = ece(probs_oof, y_oof)
    ece_after = ece(probs_cal, y_oof)

    print(f"Temperature: T={T:.4f}")
    print(f"NLL: {nll_before:.4f} -> {nll_after:.4f}")
    print(f"ECE: {ece_before:.4f} -> {ece_after:.4f}")

    # 2. Ambang per spesies dari OOF
    thresholds, global_th = find_per_species_thresholds(probs_oof, y_oof, label_map)
    n_global = sum(1 for v in thresholds.values() if v == global_th)
    print(f"Ambang: {len(thresholds)} spesies, {n_global} pakai ambang global ({global_th:.3f})")

    # 3. Simpan
    # Format datar untuk runtime (hanya ambang per spesies)
    OUT_OOF_META.parent.mkdir(parents=True, exist_ok=True)
    OUT_THRESHOLDS.write_text(json.dumps(thresholds, indent=2, ensure_ascii=False))
    print(f"Ambang runtime disimpan ke {OUT_THRESHOLDS}")

    # Metadata OOF lengkap untuk referensi
    oof_meta = {
        "source": "oof_cv",
        "temperature": round(T, 4),
        "bias": [round(float(b), 6) for b in bias],
        "global_threshold": round(global_th, 4),
        "n_using_global_threshold": n_global,
        "min_positif_untuk_threshold_per_spesies": MIN_POSITIF_OOF,
        "ece_oof_before": round(ece_before, 4),
        "ece_oof_after": round(ece_after, 4),
        "nll_before": round(nll_before, 4),
        "nll_after": round(nll_after, 4),
    }
    OUT_OOF_META.write_text(json.dumps(oof_meta, indent=2, ensure_ascii=False))
    print(f"Metadata OOF disimpan ke {OUT_OOF_META}")
    return 0


if __name__ == "__main__":
    sys.exit(main())