"""Helper load model + temperature+bias calibration yang dibundle di best_model.npz.

Mengikuti recipe ml/engines/embedding_clf.py: inferensi produksi ambil raw logits
dari MLP, terapkan (logits + bias) / T, lalu softmax. Untuk evaluasi paper-grade
kita pakai cara yang sama, bukan raw MLP output.

Pakai:
    from ml.model_loader import load_model_with_calibration
    probs = load_model_with_calibration(X)  # X sudah dinormalisasi

"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from ml.train import MLP

ML_DIR = Path(__file__).resolve().parent
CKPT = ML_DIR / "checkpoints" / "best_model.npz"
NORM = ML_DIR / "checkpoints" / "normalization.npz"
HIDDEN = 256


def _jalur(ckpt_dir=None):
    """Kembalikan (ckpt, norm) untuk direktori checkpoint yang diminta.

    Tanpa argumen, jalur produksi dipakai seperti sebelumnya. Model korpus v2
    (BirdNET 1024) dan Perch (1536) punya direktori sendiri, jadi evaluator
    harus bisa diarahkan tanpa mengubah berkas produksi.
    """
    if ckpt_dir is None:
        return CKPT, NORM
    d = Path(ckpt_dir)
    return d / "best_model.npz", d / "normalization.npz"


def muat(ckpt_dir=None):
    """Load model + normalization. Tidak mengembalikan probs, hanya MLP, mean, std.

    Dimensi input dibaca dari bobot checkpoint (W1 baris), bukan konstanta,
    supaya model 1024 maupun 1536 bisa dimuat helper yang sama.
    """
    ckpt_path, norm_path = _jalur(ckpt_dir)
    norm = np.load(norm_path)
    mean = norm["mean"].astype(np.float32)
    std = norm["std"].astype(np.float32)
    blob = np.load(ckpt_path)
    emb_dim = int(blob["W1"].shape[0])
    n_classes = int(blob["W2"].shape[1])
    model = MLP(emb_dim, HIDDEN, n_classes)
    model.load(str(ckpt_path))
    return model, mean, std


def dengan_kalibrasi(raw_probs: np.ndarray, ckpt_dir=None) -> np.ndarray:
    """Terapkan temperature + bias ke raw_probs MLP, sesuai rumus produksi."""
    ckpt_path, _ = _jalur(ckpt_dir)
    ckpt = np.load(ckpt_path, allow_pickle=False)
    if "temperature" not in ckpt.files or "bias" not in ckpt.files:
        return raw_probs
    T = float(ckpt["temperature"].reshape(-1)[0])
    bias = ckpt["bias"].astype(np.float32)
    eps = 1e-9
    p = np.clip(raw_probs, eps, 1.0)
    logits = np.log(p)
    scaled = (logits + bias) / T
    scaled -= scaled.max(axis=1, keepdims=True)
    e = np.exp(scaled)
    return e / e.sum(axis=1, keepdims=True)


def predict_normalized(X: np.ndarray) -> np.ndarray:
    """Convenience: load model, normalize X, kalibrasi, return probs."""
    model, mean, std = muat()
    raw = model.forward((X.astype(np.float32) - mean) / std)
    return dengan_kalibrasi(raw)
