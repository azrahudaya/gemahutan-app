"""Ambang per spesies: baca dan validasi thresholds.json.

Semua pembaca thresholds.json wajib lewat sini supaya skema selalu divalidasi.
Format yang sah: dict[str, float] dengan kunci persis label_map.json,
nilai 0.0 sampai 1.0. Format bersarang (source/temperature/bias/thresholds)
atau format lain akan ditolak keras.

Gunakan:
    from ml.ambang import muat_ambang
    ambang = muat_ambang()  # -> dict[str, float]
"""

from __future__ import annotations

import json
from pathlib import Path

ML_DIR = Path(__file__).resolve().parent
THRESHOLDS_PATH = ML_DIR / "reports" / "thresholds.json"
LABEL_MAP_PATH = ML_DIR / "checkpoints" / "label_map.json"


def muat_label_map() -> dict[str, int]:
    """Baca label_map.json untuk daftar spesies yang sah."""
    with open(LABEL_MAP_PATH) as f:
        return json.load(f)


def muat_ambang(path: Path | None = None) -> dict[str, float]:
    """Baca thresholds.json dan validasi skema.

    Validasi:
    - Harus dict[str, float/int] (bukan nested object)
    - Kunci persis == label_map.json (26 kelas: 25 spesies + _negative)
    - Semua nilai antara 0.0 dan 1.0

    Raises:
        ValueError: skema tidak valid
        FileNotFoundError: berkas tidak ditemukan
    """
    p = Path(path) if path else THRESHOLDS_PATH
    if not p.exists():
        raise FileNotFoundError(f"thresholds.json tidak ditemukan: {p}")

    with open(p) as f:
        data = json.load(f)

    label_map = muat_label_map()

    # Validasi: harus dict dengan nilai numerik (bukan nested)
    if not isinstance(data, dict):
        raise ValueError(
            f"thresholds.json harus dict, bukan {type(data).__name__}"
        )

    # Cek apakah ini format bersarang (ada kunci 'thresholds' di dalam)
    if "thresholds" in data and isinstance(data.get("thresholds"), dict):
        raise ValueError(
            "thresholds.json pakai format bersarang (source/temperature/bias/thresholds). "
            "Gunakan format datar: {spesies: ambang, ...}"
        )

    # Validasi tiap nilai: harus float/int dan 0.0-1.0
    for key, val in data.items():
        if not isinstance(val, (int, float)):
            raise ValueError(
                f"Nilai thresholds['{key}'] harus numerik, "
                f"bukan {type(val).__name__}: {val!r}"
            )
        if not (0.0 <= val <= 1.0):
            raise ValueError(
                f"Nilai thresholds['{key}'] = {val} di luar rentang [0, 1]"
            )

    # Validasi kunci: harus persis label_map
    expected = set(label_map.keys())
    actual = set(data.keys())
    if actual != expected:
        missing = expected - actual
        extra = actual - expected
        msg = "Kunci thresholds tidak cocok dengan label_map."
        if missing:
            msg += f" Hilang: {sorted(missing)}."
        if extra:
            msg += f" Tambahan: {sorted(extra)}."
        raise ValueError(msg)

    return {k: float(v) for k, v in data.items()}