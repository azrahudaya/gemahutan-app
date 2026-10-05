"""Snapshot test untuk model GemaHutan.

Setiap run, load best_model.npz + thresholds + normalization. Untuk 10
klip gold yang sudah ada di apps/api/tests/fixtures/model_snapshots.json,
jalankan prediksi ulang dan bandingkan hasil (label, confidence) dengan
nilai di fixture. Drift > 1e-3 -> test FAIL.

Fixture sudah berisi embedding 1024-dim per klip (dihasilkan oleh
ml/build_snapshot.py), sehingga test ini tidak perlu BirdNET interpreter
maupun embeddings.npy di host. Cocok untuk dijalankan di host dan di
container api.

Penggunaan:
  pytest tests/test_model_snapshot.py -v
  docker compose exec -T api python -m pytest tests/test_model_snapshot.py -v
"""
import json
import sys
from pathlib import Path

import numpy as np
import pytest

# Cari root repo: jalan ke atas sampai ketemu folder ml/ + fixtures/model_snapshots.json.
_HERE = Path(__file__).resolve()
_candidate = _HERE.parent
REPO = None
while _candidate != _candidate.parent:
    if (_candidate / "ml" / "checkpoints" / "best_model.npz").exists():
        for cand_fix in [
            _candidate / "apps" / "api" / "tests" / "fixtures"
                         / "model_snapshots.json",
            _candidate / "tests" / "fixtures" / "model_snapshots.json",
        ]:
            if cand_fix.exists():
                REPO = _candidate
                break
    if REPO:
        break
    _candidate = _candidate.parent
if REPO is None:
    REPO = _HERE.parents[3]

ML = REPO / "ml"
SNAPSHOT_AUDIO = ML / "tests" / "snapshot_audio"
FIXTURE_CANDIDATES = [
    REPO / "apps" / "api" / "tests" / "fixtures" / "model_snapshots.json",
    REPO / "tests" / "fixtures" / "model_snapshots.json",
]
FIXTURE = next((p for p in FIXTURE_CANDIDATES if p.exists()), FIXTURE_CANDIDATES[0])

sys.path.insert(0, str(REPO))
sys.path.insert(0, str(ML))

THR = ML / "reports" / "thresholds.json"

TOL = 1e-3  # Drift keyakinan yang ditoleransi. Sebelumnya 0.10 dengan alasan
               # "beda float lintas Python", padahal alasan sebenarnya adalah
               # dropout yang masih aktif saat inference: nilai keyakinan berubah
               # tiap pemanggilan sehingga toleransi longgar dipasang supaya test
               # tidak merah. Setelah MLP.load() menutup dropout, drift terukur
               # 0,00000000 pada 10 klip snapshot. Batas 1e-3 tetap memberi ruang
               # untuk beda urutan reduce BLAS antar versi (orde 1e-6), tapi
               # regresi ketidakstabilan sekecil 0,01 sudah tertangkap.


def _muat_engine():
    """Muat EmbeddingClassifierEngine (jalur produksi). TFLite di-stub."""
    from ml.engines.embedding_clf import EmbeddingClassifierEngine

    engine = EmbeddingClassifierEngine.__new__(EmbeddingClassifierEngine)
    EmbeddingClassifierEngine.__init__(engine)
    engine._load_birdnet_interpreter = lambda: None
    engine._ensure_loaded()
    label_map = engine._label_map
    inv = engine._inv_label_map
    return engine, label_map, inv


def _prediksi_via_engine(engine, X, label_map, thr):
    """Prediksi lewat engine._calibrated_probs + threshold (jalur produksi)."""
    x_norm = ((X.astype(np.float32) - engine._mean) / engine._std)
    probs = engine._calibrated_probs(x_norm)
    preds = np.zeros(len(X), dtype=int)
    confs = np.zeros(len(X), dtype=np.float64)
    for i in range(len(X)):
        diizinkan = [c for c, nama in enumerate(label_map)
                     if probs[i, c] >= thr.get(nama, 0.0)]
        if not diizinkan:
            diizinkan = [int(np.argmax(probs[i]))]
        preds[i] = diizinkan[np.argmax(probs[i, diizinkan])]
        confs[i] = float(probs[i, preds[i]])
    return preds, confs


@pytest.fixture(scope="module")
def snapshot():
    if not FIXTURE.exists():
        pytest.skip(f"Snapshot fixture belum ada: {FIXTURE}")
    return json.loads(FIXTURE.read_text())


def test_snapshot_audio_ada():
    """Folder snapshot_audio harus berisi 10 klip dengan nama sesuai snapshot."""
    assert SNAPSHOT_AUDIO.exists(), f"snapshot_audio tidak ada: {SNAPSHOT_AUDIO}"
    files = sorted(p.name for p in SNAPSHOT_AUDIO.glob("*.wav")) + \
            sorted(p.name for p in SNAPSHOT_AUDIO.glob("*.mp3"))
    assert len(files) == 10, (
        f"expected 10 audio snapshot, found {len(files)}: {files}"
    )


def test_snapshot_predict(snapshot):
    """Prediksi ulang 10 klip snapshot, bandingkan dengan fixture."""
    engine, label_map, inv = _muat_engine()
    thr = json.loads(THR.read_text())
    clips = snapshot["clips"]
    drift_found = []
    for ent in clips:
        emb = np.array(ent["embedding"], dtype=np.float32)
        X = emb.reshape(1, -1)
        preds, confs = _prediksi_via_engine(engine, X, label_map, thr)
        pred_label = inv[int(preds[0])]
        conf = float(confs[0])
        if pred_label != ent["expected_label"]:
            drift_found.append(
                f"{ent['clip_id']}: label drift "
                f"{ent['expected_label']} -> {pred_label}"
            )
        if abs(conf - ent["expected_confidence"]) > TOL:
            drift_found.append(
                f"{ent['clip_id']}: confidence drift "
                f"{ent['expected_confidence']:.4f} -> {conf:.4f}"
            )
    assert not drift_found, "snapshot drift:\n  " + "\n  ".join(drift_found)


def test_snapshot_jumlah_dan_label_unik(snapshot):
    """Sanity: snapshot berisi 10 klip, label unik minimal 5 kelas berbeda."""
    clips = snapshot["clips"]
    assert len(clips) == 10, f"expected 10 clips, got {len(clips)}"
    label_unik = {c["expected_label"] for c in clips}
    assert len(label_unik) >= 5, f"expected >=5 unique labels, got {len(label_unik)}"


def test_inference_deterministik(snapshot):
    """engine._calibrated_probs harus memberi hasil identik pada pemanggilan berulang.

    Jalur produksi (EmbeddingClassifierEngine) dipakai, bukan matmul manual.
    Dropout harus mati saat inference; kalau aktif, hasil berubah tiap panggil.
    """
    engine, label_map, _inv = _muat_engine()
    assert not engine._model.training, (
        "dropout masih aktif setelah load, inference tidak deterministik"
    )

    emb = np.array(snapshot["clips"][0]["embedding"], dtype=np.float32).reshape(1, -1)
    x_norm = ((emb - engine._mean) / engine._std).astype(np.float32)

    pertama = engine._calibrated_probs(x_norm)
    for ulang in range(2, 8):
        lagi = engine._calibrated_probs(x_norm)
        assert np.array_equal(pertama, lagi), (
            f"_calibrated_probs berubah pada pemanggilan ke-{ulang}: "
            f"argmax {int(np.argmax(pertama))} -> {int(np.argmax(lagi))}, "
            f"selisih maksimum {float(np.max(np.abs(pertama - lagi))):.6f}"
        )