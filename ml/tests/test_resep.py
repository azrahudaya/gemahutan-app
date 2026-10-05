"""Test: resep.py reproduksi LR v3 pada split v3.

Dua mode diuji:
  normalisasi="produksi"  -- harus reproduksi 0,7795 (selisih <= 0,005)
  normalisasi="lipatan"   -- akurasi lebih rendah, terdokumentasi

Jalankan: pytest ml/tests/test_resep.py -q
"""

import json
import sys
from pathlib import Path

import numpy as np
import pytest

ML_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ML_DIR.parent))

from ml.resep import latih, prediksi  # noqa: E402


def _muat_data_v3():
    """Muat embeddings_v3, label, splits."""
    emb_dir = ML_DIR / "embeddings_v3"
    splits_file = ML_DIR / "data" / "splits_v3.json"
    if not emb_dir.exists():
        pytest.skip("embeddings_v3 tidak ada (gitignored)")
    if not splits_file.exists():
        pytest.skip("splits_v3.json tidak ada (gitignored)")

    emb = np.load(emb_dir / "embeddings.npy")
    lab = np.load(emb_dir / "labels.npy")
    ids = json.loads((emb_dir / "clip_ids.json").read_text())
    label_map = json.loads((emb_dir / "label_map.json").read_text())
    sp = json.loads(splits_file.read_text())
    idx = {cid: i for i, cid in enumerate(ids)}

    tr = [c for c in sp["train"] if c in idx]
    val = [c for c in sp["val"] if c in idx]
    test = [c for c in sp["test"] if c in idx]

    X_tr = emb[[idx[c] for c in tr]]
    y_tr = lab[[idx[c] for c in tr]]
    X_val = emb[[idx[c] for c in val]]
    y_val = lab[[idx[c] for c in val]]
    X_test = emb[[idx[c] for c in test]]
    y_test = lab[[idx[c] for c in test]]

    return X_tr, y_tr, X_val, y_val, X_test, y_test, label_map


def test_resep_produksi_mereproduksi_lr_v3():
    """Mode normalisasi=produksi harus mereproduksi LR v3: selisih <= 0,005.

    LR v3 dilatih dengan save_logreg.py: normalisasi dari checkpoints_v2,
    LogisticRegression C=1.0, seed=2024, class_weight=balanced.
    Akurasi terkalibrasi di test set = 0,7795.
    """
    X_tr, y_tr, X_val, y_val, X_test, y_test, label_map = _muat_data_v3()

    ckpt_norm = ML_DIR / "checkpoints_v2" / "normalization.npz"
    if not ckpt_norm.exists():
        pytest.skip("checkpoints_v2/normalization.npz tidak ada (gitignored)")

    konfigurasi = {"C": 1.0, "seed": 2024, "maks_negatif": 3000}
    model = latih([], konfigurasi, X_tr, y_tr, label_map, X_val, y_val,
                   normalisasi="produksi", ckpt_norm=ckpt_norm)

    # Akurasi terkalibrasi (metrik produksi)
    probs = prediksi(model, X_test)
    cal_acc = float(np.mean(np.argmax(probs, axis=1) == y_test))

    baseline = 0.7795
    selisih = abs(cal_acc - baseline)
    print(f"Calibrated accuracy: {cal_acc:.4f} (baseline LR v3: {baseline}, "
          f"selisih: {selisih:.4f})")

    assert selisih <= 0.005, (
        f"Selisih {selisih:.4f} > 0.005 dari baseline LR v3 ({baseline}). "
        f"Resep normalisasi=produksi tidak mereproduksi LR v3."
    )


def test_resep_lipatan_akurasi_lebih_rendah():
    """Mode normalisasi=lipatan: akurasi lebih rendah, tapi tetap >= 0,70.

    Normalisasi dari data latih sendiri menghasilkan distribusi berbeda
    dari normalisasi checkpoints_v2. Ini perilaku yang diharapkan.
    Kalibrasi tidak boleh menurunkan akurasi > 3 poin dari mentah.
    """
    X_tr, y_tr, X_val, y_val, X_test, y_test, label_map = _muat_data_v3()

    konfigurasi = {"C": 1.0, "seed": 2024, "maks_negatif": 3000}
    model = latih([], konfigurasi, X_tr, y_tr, label_map, X_val, y_val,
                   normalisasi="lipatan")

    # Akurasi mentah (tanpa kalibrasi)
    X_test_norm = ((X_test.astype(np.float32) - model.mean) / model.std)
    logits_raw = X_test_norm @ model.mlp.W1 + model.mlp.b1
    raw_acc = float(np.mean(np.argmax(logits_raw, axis=1) == y_test))

    # Akurasi terkalibrasi
    probs = prediksi(model, X_test)
    cal_acc = float(np.mean(np.argmax(probs, axis=1) == y_test))

    print(f"Raw accuracy: {raw_acc:.4f}")
    print(f"Calibrated accuracy: {cal_acc:.4f}")
    print(f"Calibration delta: {cal_acc - raw_acc:+.4f}")

    # Kalibrasi tidak boleh menurunkan akurasi lebih dari 3 poin
    delta = cal_acc - raw_acc
    assert delta > -0.03, (
        f"Kalibrasi menurunkan akurasi {delta:.4f} (> 3 poin). "
        f"Ada bug di fit bias/T."
    )
    assert raw_acc >= 0.70, f"Raw accuracy {raw_acc:.4f} < 0.70"


def test_resep_model_linear():
    """Pastikan model dari resep adalah linear (W2 identitas, b2 nol)."""
    rng = np.random.default_rng(42)
    X = rng.normal(size=(100, 4)).astype(np.float32)
    y = rng.integers(0, 3, size=100)
    label_map = {"a": 0, "b": 1, "c": 2}

    model = latih(["clip1"] * 50, {"C": 1.0, "seed": 2024, "maks_negatif": 3000},
                   X, y, label_map)

    assert np.allclose(model.mlp.W2, np.eye(3), atol=1e-5), "W2 bukan identitas"
    assert np.allclose(model.mlp.b2, np.zeros(3), atol=1e-5), "b2 bukan nol"

    probs = prediksi(model, X[:10])
    assert probs.shape == (10, 3)
    assert np.allclose(probs.sum(axis=1), 1.0, atol=1e-5)