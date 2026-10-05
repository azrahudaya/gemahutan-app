"""Test paritas: EmbeddingClassifierEngine == model_loader.

Regression guard: probabilitas dari embedding_clf harus identik dengan
model_loader. Pakai fixture checkpoint linear kecil dari ml/tests/fixtures/
supaya tidak bergantung folder embeddings_v3 yang di-ignore.
"""

import sys
from pathlib import Path

import numpy as np
import pytest

# Cari root repo: jalan ke atas sampai ketemu folder ml/.
_HERE = Path(__file__).resolve()
ROOT = _HERE
while ROOT != ROOT.parent and not (ROOT / "ml" / "tests" / "fixtures").exists():
    ROOT = ROOT.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

FIXTURE_DIR = ROOT / "ml" / "tests" / "fixtures"


def _buat_embedding_test(n_samples=20, dim=4, seed=42):
    """Buat embedding sintetis untuk test dengan dimensi fixture."""
    rng = np.random.default_rng(seed)
    return rng.normal(size=(n_samples, dim)).astype(np.float32)


@pytest.fixture(scope="module")
def embeddings_sample():
    """Embedding sintetis 4-dim sesuai fixture."""
    return _buat_embedding_test(20)


@pytest.fixture(scope="module")
def ckpt_fixture():
    """Path ke fixture checkpoint."""
    ckpt = FIXTURE_DIR / "best_model.npz"
    norm = FIXTURE_DIR / "normalization.npz"
    if not ckpt.exists() or not norm.exists():
        pytest.skip("Fixture checkpoint belum ada. Jalankan: python3 ml/tests/fixtures/")
    return ckpt, norm


def test_paritas_raw_logits_vs_forward(embeddings_sample, ckpt_fixture):
    """_raw_logits harus sama dengan z2 dari MLP.forward()."""
    ckpt, norm_path = ckpt_fixture

    from ml.train import MLP

    norm_data = np.load(norm_path)
    mean = norm_data["mean"].astype(np.float32)
    std = norm_data["std"].astype(np.float32)

    ckpt_data = np.load(ckpt)
    emb_dim = int(ckpt_data["W1"].shape[0])
    n_classes = int(ckpt_data["W2"].shape[1])
    hidden = 256

    model = MLP(emb_dim, hidden, n_classes)
    model.load(str(ckpt))
    model.training = False

    X = (embeddings_sample - mean) / std

    model.forward(X)
    z2_forward = model.z2

    from ml.engines.embedding_clf import EmbeddingClassifierEngine

    # Monkey-patch agar tidak load TFLite
    engine = EmbeddingClassifierEngine.__new__(EmbeddingClassifierEngine)
    engine._model = model
    engine._mean = mean
    engine._std = std

    raw_clf = engine._raw_logits(X)

    np.testing.assert_allclose(raw_clf, z2_forward, atol=1e-5,
                               err_msg="_raw_logits != MLP.z2 (logits)")


def test_paritas_calibrated_probs_vs_model_loader(embeddings_sample, ckpt_fixture):
    """Probabilitas kalibrasi embedding_clf harus sama dengan model_loader."""
    ckpt, norm_path = ckpt_fixture

    from ml.engines.embedding_clf import EmbeddingClassifierEngine
    from ml.model_loader import dengan_kalibrasi, muat

    # Jalur 1: model_loader (pakai fixture)
    ckpt_dir_str = str(FIXTURE_DIR)
    model, mean, std = muat(ckpt_dir=ckpt_dir_str)
    X_norm = (embeddings_sample.astype(np.float32) - mean) / std
    raw = model.forward(X_norm)
    probs_loader = dengan_kalibrasi(raw, ckpt_dir=ckpt_dir_str)

    # Jalur 2: EmbeddingClassifierEngine._calibrated_probs
    engine = EmbeddingClassifierEngine.__new__(EmbeddingClassifierEngine)
    engine._model = model
    engine._mean = mean
    engine._std = std
    engine._temperature = 1.0
    engine._bias = None

    ckpt_data = np.load(ckpt)
    if "temperature" in ckpt_data.files:
        engine._temperature = float(ckpt_data["temperature"][0])
    if "bias" in ckpt_data.files:
        engine._bias = np.asarray(ckpt_data["bias"], dtype=np.float32)

    probs_clf = engine._calibrated_probs(X_norm)

    np.testing.assert_allclose(probs_clf, probs_loader, atol=1e-5,
                               err_msg="kalibrasi embedding_clf != model_loader")


def test_paritas_predict_logits_vs_forward(embeddings_sample, ckpt_fixture):
    """MLP.predict_logits harus hormati activation, bukan selalu ReLU."""
    ckpt, norm_path = ckpt_fixture

    from ml.train import MLP

    norm_data = np.load(norm_path)
    mean = norm_data["mean"].astype(np.float32)
    std = norm_data["std"].astype(np.float32)

    ckpt_data = np.load(ckpt)
    emb_dim = int(ckpt_data["W1"].shape[0])
    n_classes = int(ckpt_data["W2"].shape[1])
    hidden = 256

    model = MLP(emb_dim, hidden, n_classes)
    model.load(str(ckpt))
    model.training = False

    X_norm = (embeddings_sample - mean) / std

    logits = model.predict_logits(X_norm)
    model.forward(X_norm)
    z2_forward = model.z2

    np.testing.assert_allclose(logits, z2_forward, atol=1e-5,
                               err_msg="predict_logits != z2 (ReLU bug?)")