"""Test cascade gate + paritas dengan 07947bc.

(a) Konfigurasi yang dimuat cascade = MANIFEST.cascade_config_sha256.
(b) Keluaran CascadeEngine pada 8 klip demo = paritas_07947bc.json.
"""
import json
import sys
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve()
ROOT = _HERE
while ROOT != ROOT.parent and not (ROOT / "ml" / "tests" / "fixtures").exists():
    ROOT = ROOT.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PARITAS_FILE = ROOT / "ml" / "reports" / "paritas_07947bc.json"


def _sha256_file(path):
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


class TestCascadeGate:
    """Konfigurasi cascade = MANIFEST, hasil = 07947bc."""

    def test_cascade_yaml_sama_dengan_manifest(self):
        """Sha256 cascade.yaml == MANIFEST.cascade_config_sha256."""
        manifest = json.loads(
            (ROOT / "ml" / "checkpoints" / "MANIFEST.json").read_text()
        )
        expected = manifest["cascade_config_sha256"]
        actual = _sha256_file(ROOT / "ml" / "configs" / "cascade.yaml")
        assert actual == expected, (
            f"cascade.yaml sha256 {actual[:16]} != MANIFEST {expected[:16]}"
        )

    def test_8_klip_demo_identik_07947bc(self):
        """Deteksi CascadeEngine pada 8 klip demo == paritas_07947bc.json."""
        from ml.engines.cascade import CascadeEngine  # noqa: E402

        expected = json.loads(PARITAS_FILE.read_text())
        engine = CascadeEngine()
        engine._ensure_loaded()
        demo = sorted((ROOT / "ml" / "demo_audio").glob("*.mp3"))

        for mp3 in demo[:8]:
            hasil = engine.predict(str(mp3))
            exp = expected[mp3.name]
            assert len(hasil) == len(exp), (
                f"{mp3.name}: {len(hasil)} deteksi != {len(exp)}"
            )
            for a, e in zip(hasil, exp, strict=True):
                assert a.species_scientific == e["species"], (
                    f"{mp3.name}: {a.species_scientific} != {e['species']}"
                )
                assert a.start_s == pytest.approx(e["start_s"], abs=0.5), (
                    f"{mp3.name}: start {a.start_s} != {e['start_s']}"
                )
                assert a.end_s == pytest.approx(e["end_s"], abs=0.5), (
                    f"{mp3.name}: end {a.end_s} != {e['end_s']}"
                )