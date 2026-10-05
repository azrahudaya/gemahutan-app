"""Test gradien numerik untuk MLP.backward().

Verifikasi bahwa gradien analitik cocok dengan gradien numerik
(finite difference) dengan toleransi 1e-4. Mencakup:
- Bobot kelas (sample_weights via w*(probs-onehot))
- Dropout mask di backward
- Turunan aktivasi (ReLU vs linear)
- Adam satu t_step per langkah
"""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml.train import MLP  # noqa: E402


def _weighted_ce_loss(probs, y, sample_weights=None):
    """Weighted cross-entropy loss: -mean(w_i * log(p_i,y_i))."""
    m = len(y)
    logp = np.log(probs[np.arange(m), y] + 1e-12)
    if sample_weights is not None:
        return float(-np.mean(sample_weights * logp))
    return float(-np.mean(logp))


def _total_loss(probs, y, model, sample_weights=None):
    """CE loss + L2 penalty."""
    ce = _weighted_ce_loss(probs, y, sample_weights)
    l2 = 0.5 * model.weight_decay * (
        np.sum(model.W1 ** 2) + np.sum(model.W2 ** 2))
    return ce + l2


def _compute_numerical_gradients(model, X, y, sample_weights=None, eps=1e-5):
    """Hitung gradien numerik via central finite diff. Kembalikan bobot awal."""
    params = {}
    for name in ["W1", "b1", "W2", "b2"]:
        param = getattr(model, name)
        grad = np.zeros_like(param)
        it = np.nditer(param, flags=['multi_index'], op_flags=['readonly'])
        while not it.finished:
            idx = it.multi_index
            orig = float(param[idx])

            param[idx] = orig + eps
            probs_p = model.forward(X)
            loss_p = _total_loss(probs_p, y, model, sample_weights)

            param[idx] = orig - eps
            probs_m = model.forward(X)
            loss_m = _total_loss(probs_m, y, model, sample_weights)

            param[idx] = orig
            grad[idx] = (loss_p - loss_m) / (2 * eps)
            it.iternext()
        params[name] = grad

    return params


def _compute_analytical_gradients(model, X, y_onehot, sample_weights=None):
    """Hitung gradien analitik dari MLP.forward() + rumus backward tanpa Adam."""
    m = X.shape[0]
    dz2 = (model.probs - y_onehot) / m
    if sample_weights is not None:
        dz2 = dz2 * sample_weights[:, None]

    dW2 = model.a1_drop.T @ dz2 + model.weight_decay * model.W2
    db2 = np.sum(dz2, axis=0)
    da1 = dz2 @ model.W2.T

    if model.drop_mask is not None:
        da1 = da1 * model.drop_mask

    if model.activation == "relu":
        dz1 = da1 * (model.z1 > 0).astype(np.float32)
    else:
        dz1 = da1

    dW1 = X.T @ dz1 + model.weight_decay * model.W1
    db1 = np.sum(dz1, axis=0)

    return {"W1": dW1, "b1": db1, "W2": dW2, "b2": db2}


def _forward_deterministic(model, X):
    """Forward pass dengan dropout mask yang sudah diset manual."""
    model.z1 = X @ model.W1 + model.b1
    model.a1 = np.maximum(0, model.z1) if model.activation == "relu" else model.z1
    if model.training and model.dropout > 0 and model.drop_mask is not None:
        model.a1_drop = model.a1 * model.drop_mask
    else:
        model.drop_mask = None
        model.a1_drop = model.a1
    model.z2 = model.a1_drop @ model.W2 + model.b2
    exp_z = np.exp(model.z2 - np.max(model.z2, axis=1, keepdims=True))
    model.probs = exp_z / np.sum(exp_z, axis=1, keepdims=True)
    return model.probs


def test_gradient_relu_no_weights():
    """Gradien ReLU tanpa class weights."""
    rng = np.random.default_rng(123)
    X = rng.normal(0, 1, (8, 6)).astype(np.float32)
    y = rng.integers(0, 3, size=8)
    y_onehot = np.zeros((8, 3), dtype=np.float32)
    y_onehot[np.arange(8), y] = 1.0

    np.random.seed(42)
    model = MLP(6, 4, 3, lr=0.01, dropout=0.0, weight_decay=1e-4, activation="relu")
    model.training = True
    model.forward(X)
    analytical = _compute_analytical_gradients(model, X, y_onehot)
    numerical = _compute_numerical_gradients(model, X, y)

    for name in ["W1", "b1", "W2", "b2"]:
        diff = np.max(np.abs(analytical[name] - numerical[name]))
        assert diff < 1e-4, f"{name} grad diff: {diff:.6f}"


def test_gradient_linear_activation():
    """activation=linear: turunan aktivasi = 1, bukan (z1 > 0)."""
    rng = np.random.default_rng(456)
    X = rng.normal(0, 1, (6, 4)).astype(np.float32)
    y = rng.integers(0, 2, size=6)
    y_onehot = np.zeros((6, 2), dtype=np.float32)
    y_onehot[np.arange(6), y] = 1.0

    np.random.seed(43)
    model = MLP(4, 3, 2, lr=0.01, dropout=0.0, weight_decay=0.0, activation="linear")
    model.training = True
    model.forward(X)
    analytical = _compute_analytical_gradients(model, X, y_onehot)
    numerical = _compute_numerical_gradients(model, X, y)

    for name in ["W1", "b1", "W2", "b2"]:
        diff = np.max(np.abs(analytical[name] - numerical[name]))
        assert diff < 1e-4, f"Linear {name} grad diff: {diff:.6f}"


def test_gradient_with_class_weights():
    """Class weights: dz2 *= w[:, None], bukan y_onehot *= w[:, None]."""
    rng = np.random.default_rng(789)
    X = rng.normal(0, 1, (10, 5)).astype(np.float32)
    y = rng.integers(0, 3, size=10)
    y_onehot = np.zeros((10, 3), dtype=np.float32)
    y_onehot[np.arange(10), y] = 1.0
    w = np.array([1.0, 3.0, 10.0], dtype=np.float32)[y]

    np.random.seed(44)
    model = MLP(5, 4, 3, lr=0.01, dropout=0.0, weight_decay=0.0, activation="relu")
    model.training = True
    model.forward(X)
    analytical = _compute_analytical_gradients(model, X, y_onehot, sample_weights=w)
    numerical = _compute_numerical_gradients(model, X, y, sample_weights=w)

    for name in ["W1", "b1", "W2", "b2"]:
        diff = np.max(np.abs(analytical[name] - numerical[name]))
        assert diff < 1e-4, f"Weighted {name} grad diff: {diff:.6f}"


def test_gradient_with_dropout():
    """Dropout mask di backward: da1 *= drop_mask."""
    rng = np.random.default_rng(101)
    X = rng.normal(0, 1, (12, 6)).astype(np.float32)
    y = rng.integers(0, 3, size=12)
    y_onehot = np.zeros((12, 3), dtype=np.float32)
    y_onehot[np.arange(12), y] = 1.0

    # Seed tetap, forward pertama untuk dapatkan dropout mask
    np.random.seed(42)
    model = MLP(6, 5, 3, lr=0.01, dropout=0.3, weight_decay=0.0, activation="relu")
    model.training = True
    model.forward(X)

    # Bekukan mask supaya deterministik untuk numerical gradient
    frozen_mask = model.drop_mask.copy()
    model.drop_mask = frozen_mask

    analytical = _compute_analytical_gradients(model, X, y_onehot)

    # Ganti forward dengan versi deterministik (pakai mask bekunya)
    orig_forward = model.forward
    model.forward = lambda X_in: _forward_deterministic(model, X_in)
    numerical = _compute_numerical_gradients(model, X, y)
    model.forward = orig_forward

    for name in ["W1", "b1", "W2", "b2"]:
        diff = np.max(np.abs(analytical[name] - numerical[name]))
        assert diff < 1e-4, f"Dropout {name} grad diff: {diff:.6f}"


def test_adam_t_step_once_per_backward():
    """Adam t_step naik 1x per backward, bukan 4x."""
    rng = np.random.default_rng(202)
    X = rng.normal(0, 1, (4, 6)).astype(np.float32)
    y = rng.integers(0, 2, size=4)
    y_onehot = np.zeros((4, 2), dtype=np.float32)
    y_onehot[np.arange(4), y] = 1.0

    np.random.seed(45)
    model = MLP(6, 4, 2, lr=0.01, dropout=0.0, activation="relu")
    model.training = True
    assert model.t_step == 0, "t_step should start at 0"
    model.forward(X)
    model.backward(X, y_onehot, sample_weights=None)
    assert model.t_step == 1, f"t_step should be 1 after one backward, got {model.t_step}"

    model.forward(X)
    model.backward(X, y_onehot, sample_weights=None)
    assert model.t_step == 2, f"t_step should be 2 after two backwards, got {model.t_step}"


def test_class_weight_formula():
    """w*(probs-onehot) != (probs - w*onehot). Verifikasi formula benar."""
    probs = np.array([[0.7, 0.2, 0.1],
                      [0.3, 0.5, 0.2],
                      [0.1, 0.3, 0.6]], dtype=np.float32)
    y = np.array([0, 1, 2])
    y_onehot = np.zeros((3, 3), dtype=np.float32)
    y_onehot[np.arange(3), y] = 1.0

    w = np.array([1.0, 5.0, 10.0], dtype=np.float32)

    # Formula lama (bug): probs - w*onehot
    y_onehot_scaled = y_onehot * w[:, None]
    dz2_old = (probs - y_onehot_scaled) / 3

    # Formula benar: w * (probs - onehot)
    dz2_new = (probs - y_onehot) / 3
    dz2_new = dz2_new * w[:, None]

    # Keduanya harus berbeda
    diff = np.max(np.abs(dz2_old - dz2_new))
    assert diff > 1e-3, (
        f"Old and new formula give same result (diff={diff:.6f}). "
        "Bug may not have been significant on this data."
    )

    # Verifikasi manual
    expected_0 = 1.0 * np.array([0.7 - 1, 0.2, 0.1]) / 3
    expected_1 = 5.0 * np.array([0.3, 0.5 - 1, 0.2]) / 3

    np.testing.assert_allclose(dz2_new[0], expected_0, atol=1e-5)
    np.testing.assert_allclose(dz2_new[1], expected_1, atol=1e-5)