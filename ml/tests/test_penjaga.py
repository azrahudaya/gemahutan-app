"""Test penjaga artefak checkpoints/: MANIFEST, paritas, snapshot.

Jalankan: pytest ml/tests/ -q
"""

import json
from pathlib import Path

import numpy as np
import pytest

ML_DIR = Path(__file__).resolve().parent.parent
CHECKPOINTS = ML_DIR / "checkpoints"
MANIFEST_PATH = CHECKPOINTS / "MANIFEST.json"
CASCADE_PRODUKSI = ML_DIR / "configs" / "cascade.yaml"

# sha256 cascade.yaml produksi (perilaku LR v3 di commit 07947bc).
# Nilai ini SENGAJA dipaku. Kalau test ini gagal, berarti berkas konfigurasi
# produksi berubah -- biasanya karena skrip sapuan menulisinya dan lupa
# memulihkan. Yang benar: sapuan menulis ke ml/runs/<id>/cascade.yaml dan
# menunjuknya lewat env GEMAHUTAN_CASCADE_CONFIG, bukan menimpa berkas ini.
# Jangan memperbarui nilai ini supaya test hijau; pulihkan berkasnya dengan
# `git checkout -- ml/configs/cascade.yaml`. Mengubah perilaku produksi hanya
# lewat gerbang G di ml/promosikan.py.
SHA_CASCADE_PRODUKSI = (
    "5fc2d62743e5b35f4b68cae8fe7e623cd8e7d7bb2e9d05ad5838c2174ab6c5ba"
)


def sha256_file(path: Path) -> str:
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def test_manifest_ada():
    """MANIFEST.json harus ada di ml/checkpoints/."""
    assert MANIFEST_PATH.exists(), (
        f"MANIFEST.json tidak ditemukan di {CHECKPOINTS}. "
        f"Jalankan: python3 ml/promosikan.py --run <run_dir>"
    )


def test_manifest_sha_cocok():
    """sha256 semua berkas di MANIFEST harus cocok dengan file asli."""
    manifest = json.loads(MANIFEST_PATH.read_text())
    files = manifest["files"]
    assert len(files) >= 4, f"MANIFEST hanya punya {len(files)} berkas, expected >= 4"

    for fname, info in files.items():
        fpath = CHECKPOINTS / fname
        assert fpath.exists(), f"{fname} ada di MANIFEST tapi tidak di disk"
        actual = sha256_file(fpath)
        expected = info["sha256"]
        assert actual == expected, (
            f"sha256 {fname} tidak cocok: MANIFEST={expected[:12]}... "
            f"disk={actual[:12]}..."
        )


def test_manifest_format_valid():
    """MANIFEST harus punya field wajib: generated_utc, git_sha, source_run, files."""
    manifest = json.loads(MANIFEST_PATH.read_text())
    for field in ["generated_utc", "git_sha", "source_run", "files"]:
        assert field in manifest, f"MANIFEST tidak punya field '{field}'"

    # Setiap file entry harus punya sha256 dan size_bytes
    for fname, info in manifest["files"].items():
        assert "sha256" in info, f"{fname} tidak punya sha256"
        assert "size_bytes" in info, f"{fname} tidak punya size_bytes"
        assert len(info["sha256"]) == 64, f"{fname} sha256 bukan 64 hex chars"


def test_cascade_produksi_tidak_berubah():
    """ml/configs/cascade.yaml produksi harus utuh.

    Sapuan parameter berulang kali meninggalkan berkas ini dalam keadaan
    termodifikasi ketika run-nya terputus di tengah. Akibatnya evaluasi
    berikutnya memakai kebijakan eksperimen tanpa ada yang menyadarinya, dan
    angkanya tidak sebanding dengan baseline.
    """
    assert CASCADE_PRODUKSI.exists(), f"{CASCADE_PRODUKSI} tidak ada"
    aktual = sha256_file(CASCADE_PRODUKSI)
    assert aktual == SHA_CASCADE_PRODUKSI, (
        "ml/configs/cascade.yaml BERUBAH dari versi produksi.\n"
        f"  diharapkan sha256 {SHA_CASCADE_PRODUKSI[:16]}...\n"
        f"  di disk sha256    {aktual[:16]}...\n"
        "Pulihkan dengan: git checkout -- ml/configs/cascade.yaml\n"
        "Kebijakan eksperimen ditulis ke ml/runs/<id>/cascade.yaml lalu "
        "ditunjuk lewat env GEMAHUTAN_CASCADE_CONFIG, JANGAN menimpa berkas "
        "produksi. Jangan memperbarui sha di test ini supaya hijau."
    )


def test_checkpoint_linear():
    """Pastikan checkpoint adalah model linear (bukan MLP dengan hidden layer)."""
    ckpt = CHECKPOINTS / "best_model.npz"
    if not ckpt.exists():
        pytest.skip("checkpoint tidak ditemukan")
    data = np.load(ckpt)
    # W2 harus matriks identitas
    W2 = data["W2"]
    assert W2.shape[0] == W2.shape[1], "W2 bukan matriks persegi"
    assert np.allclose(W2, np.eye(W2.shape[0]), atol=1e-5), (
        "W2 bukan identitas -- model bukan linear"
    )