"""Resep pelatihan dan prediksi yang dipakai CV, promosi, dan evaluasi.

Satu-satunya jalur pelatihan yang sah. Semua skrip evaluasi (CV, promosi,
evaluasi independen) wajib lewat sini supaya resep identik dengan produksi.

Dua mode normalisasi:
  normalisasi="produksi"  -- mean/std dari checkpoint eksternal (reproduksi LR v3)
  normalisasi="lipatan"   -- mean/std di-fit dari data latih (untuk CV)

API:
    from ml.resep import latih, prediksi, ModelLogReg

    model = latih(ids_latih, konfigurasi, X, y, label_map, X_val, y_val,
                  normalisasi="lipatan", ckpt_norm=None)
    probs = prediksi(model, X_uji)
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression

from ml.train import MLP


class ModelLogReg:
    """Wrapper model linear dengan kalibrasi T+bias."""

    def __init__(self, mlp: MLP, mean: np.ndarray, std: np.ndarray,
                 temperature: float, bias: np.ndarray | None,
                 label_map: dict[str, int]):
        self.mlp = mlp
        self.mean = mean
        self.std = std
        self.temperature = temperature
        self.bias = bias
        self.label_map = label_map

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Prediksi probabilitas terkalibrasi."""
        x_norm = ((X.astype(np.float32) - self.mean) / self.std)
        self.mlp.forward(x_norm)
        logits = self.mlp.z2
        if self.bias is not None:
            logits = logits + self.bias[None, :]
        logits = logits / self.temperature
        logits = logits - np.max(logits, axis=-1, keepdims=True)
        e = np.exp(logits)
        return e / np.sum(e, axis=-1, keepdims=True)


def _softmax(z: np.ndarray) -> np.ndarray:
    z = z - z.max(axis=1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


def _nll(probs: np.ndarray, y: np.ndarray) -> float:
    return float(np.mean(-np.log(probs[np.arange(len(y)), y] + 1e-9)))


def _fit_temperature(logits: np.ndarray, y: np.ndarray) -> float:
    """Temperature scaling via grid search (identik dengan latih_produksi.py)."""
    terbaik, nll_terbaik = 1.0, float("inf")
    for T in np.arange(0.05, 5.0, 0.005):
        nilai = _nll(_softmax(logits / T), y)
        if nilai < nll_terbaik:
            terbaik, nll_terbaik = float(T), nilai
    return terbaik


def _fit_bias(logits: np.ndarray, y: np.ndarray, T: float,
              langkah: int = 2000, lr: float = 0.05) -> np.ndarray:
    """Bias aditif per kelas via gradient descent (identik dengan latih_produksi.py)."""
    n_kelas = logits.shape[1]
    bias = np.zeros(n_kelas, dtype=np.float32)
    satu_panas = np.zeros((len(y), n_kelas), dtype=np.float32)
    satu_panas[np.arange(len(y)), y] = 1.0
    for _ in range(langkah):
        probs = _softmax((logits + bias) / T)
        grad = ((probs - satu_panas).mean(axis=0)).astype(np.float32)
        bias -= lr * grad
    return bias


def latih(ids_latih: list[str],
          konfigurasi: dict,
          X: np.ndarray,
          y: np.ndarray,
          label_map: dict[str, int],
          X_val: np.ndarray | None = None,
          y_val: np.ndarray | None = None,
          normalisasi: str = "lipatan",
          ckpt_norm: str | Path | None = None,
          ) -> ModelLogReg:
    """Latih model Logistic Regression.

    Args:
        ids_latih: daftar clip_id untuk training
        konfigurasi: dict dengan kunci C, seed, maks_negatif
        X: embedding data latih [n_latih, dim]
        y: label data latih [n_latih]
        label_map: {nama_spesies: indeks}
        X_val, y_val: data validasi untuk kalibrasi
        normalisasi: "produksi" (dari ckpt_norm) atau "lipatan" (fit sendiri)
        ckpt_norm: path ke normalization.npz (hanya untuk normalisasi="produksi")

    Returns:
        ModelLogReg siap prediksi
    """
    C = float(konfigurasi.get("C", 1.0))
    seed = int(konfigurasi.get("seed", 2024))
    maks_negatif = int(konfigurasi.get("maks_negatif", 3000))

    rng = np.random.default_rng(seed)

    # Batasi negatif
    neg_idx = label_map.get("_negative", -1)
    if neg_idx >= 0 and maks_negatif > 0:
        pos_neg = np.where(y == neg_idx)[0]
        if len(pos_neg) > maks_negatif:
            buang = rng.choice(pos_neg, size=len(pos_neg) - maks_negatif,
                               replace=False)
            mask = np.ones(len(X), dtype=bool)
            mask[buang] = False
            X = X[mask]
            y = y[mask]

    # Normalisasi
    if normalisasi == "produksi" and ckpt_norm is not None:
        norm_data = np.load(str(ckpt_norm))
        mean, std = norm_data["mean"], norm_data["std"]
    else:
        mean = X.astype(np.float32).mean(axis=0)
        std = X.astype(np.float32).std(axis=0)
        std = np.where(std < 1e-8, 1.0, std)

    Xtr_norm = ((X.astype(np.float32) - mean) / std)

    # Latih LogisticRegression
    lr = LogisticRegression(max_iter=3000, C=C, class_weight="balanced",
                            random_state=seed)
    lr.fit(Xtr_norm, y)

    # Bungkus sebagai MLP linear
    n_kelas = len(label_map)
    emb_dim = X.shape[1]
    mlp = MLP(emb_dim, n_kelas, n_kelas, dropout=0.0, activation="linear")
    mlp.W1 = np.ascontiguousarray(lr.coef_.T).astype(np.float32)
    mlp.b1 = np.ascontiguousarray(lr.intercept_).astype(np.float32)
    mlp.W2 = np.eye(n_kelas, dtype=np.float32)
    mlp.b2 = np.zeros(n_kelas, dtype=np.float32)
    mlp.training = False

    # Kalibrasi T+bias di validasi
    if X_val is not None and y_val is not None:
        Xv_norm = ((X_val.astype(np.float32) - mean) / std)
        logits_val = Xv_norm @ mlp.W1 + mlp.b1
        T = _fit_temperature(logits_val, y_val)
        bias = _fit_bias(logits_val, y_val, T)
    else:
        T, bias = 1.0, None

    return ModelLogReg(mlp=mlp, mean=mean, std=std, temperature=T,
                       bias=bias, label_map=label_map)


def prediksi(model: ModelLogReg, X: np.ndarray) -> np.ndarray:
    """Jalur prediksi yang identik dengan produksi: normalisasi + kalibrasi."""
    return model.predict(X)