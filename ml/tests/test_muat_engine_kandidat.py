"""Test regresi: muat_engine WAJIB benar-benar memakai checkpoint yang diminta.

Bug yang dijaga (ditemukan 2 Oktober 2026, ML_10): `ml/uji_independen.py`
menyetel GEMAHUTAN_CHECKPOINT_DIR lewat os.environ SETELAH mengimpor
`ml.engines.embedding_clf`. Modul itu membaca env var sekali saat impor dan
menyimpannya sebagai konstanta tingkat modul, jadi penyetelan itu tidak
berpengaruh apa pun.

Yang membuat bug ini mahal adalah kegagalannya SENYAP: skrip mencetak
"Memuat checkpoint: ml/runs/<kandidat>" sambil sebenarnya menilai checkpoint
PRODUKSI. Tiga angka uji independen kandidat (K2, K3, K6) sudah dilaporkan
dengan angka yang salah sebelum ini ketahuan, dan ketahuannya hanya karena
Perch berdimensi 1536 sehingga akhirnya menabrak error bentuk. Selama kandidat
tetap 1024 dimensi, bug ini tidak akan pernah melempar error.

Dua hal diuji:
1. Direktori checkpoint yang diminta benar-benar terpasang di modul engine.
2. Direktori checkpoint yang tidak punya best_model.npz ditolak dengan jelas,
   bukan diam-diam jatuh ke produksi.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from ml.uji_independen import muat_engine  # noqa: E402


def _ckpt_palsu(tmp_path: Path, dim: int, n_kelas: int) -> Path:
    """Buat checkpoint minimal berdimensi tertentu, bentuknya mengikuti resep LR.

    Kunci wajib mengikuti ml/train.py MLP.load: W1, b1, W2, b2, lalu lr. Bentuk
    W2 (n_kelas, n_kelas) sama dengan checkpoint produksi, karena jalur
    logistic_regression memakai lapisan kedua sebagai identitas.
    """
    d = tmp_path / "ckpt_kandidat"
    d.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(0)
    np.savez(
        d / "best_model.npz",
        W1=rng.normal(size=(dim, n_kelas)).astype(np.float32),
        b1=np.zeros(n_kelas, dtype=np.float32),
        W2=np.eye(n_kelas, dtype=np.float32),
        b2=np.zeros(n_kelas, dtype=np.float32),
        lr=np.array([0.001], dtype=np.float32),
        activation=np.array(["linear"]),
    )
    np.savez(
        d / "normalization.npz",
        mean=np.zeros(dim, dtype=np.float32),
        std=np.ones(dim, dtype=np.float32),
    )
    return d


def test_checkpoint_dir_benar_benar_dipakai(tmp_path):
    """Dimensi mean harus datang dari checkpoint kandidat, bukan produksi (1024)."""
    dim = 777  # sengaja bukan 1024 dan bukan 1536
    emb_dir = ROOT / "ml" / "embeddings_v3"
    n_kelas = len(__import__("json").loads((emb_dir / "label_map.json").read_text()))
    d = _ckpt_palsu(tmp_path, dim, n_kelas)

    import ml.engines.embedding_clf as mod

    engine = muat_engine(d, emb_dir)

    assert Path(mod.CHECKPOINT_DIR) == d, (
        f"engine memakai {mod.CHECKPOINT_DIR}, bukan {d} yang diminta"
    )
    assert len(engine._mean) == dim, (
        f"mean {len(engine._mean)} dimensi, berarti checkpoint kandidat diabaikan "
        "dan produksi yang termuat"
    )


def test_checkpoint_tanpa_model_ditolak(tmp_path):
    """Direktori tanpa best_model.npz harus gagal keras, bukan jatuh ke produksi."""
    kosong = tmp_path / "kosong"
    kosong.mkdir()
    with pytest.raises(SystemExit):
        muat_engine(kosong, ROOT / "ml" / "embeddings_v3")
