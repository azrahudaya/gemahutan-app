"""Test opsi --pengecualian pada ml/promosikan.py."""
from __future__ import annotations

import json
from pathlib import Path

from ml.promosikan import baca_pengecualian, cek_gerbang


def test_baca_pengecualian_string(tmp_path: Path):
    p = tmp_path / "pengecualian.json"
    p.write_text(
        json.dumps(
            {
                "kriteria": "spesies_turun_recall",
                "disetujui_oleh": "peninjau",
                "tanggal": "2026-10-03",
                "alasan": "derau",
            }
        )
    )
    assert baca_pengecualian(p) == ["spesies_turun_recall"]


def test_baca_pengecualian_list(tmp_path: Path):
    p = tmp_path / "pengecualian.json"
    p.write_text(json.dumps({"kriteria": ["a", "b"]}))
    assert baca_pengecualian(p) == ["a", "b"]


def test_cek_gerbang_lewat_kriteria_dikecualikan():
    g = {
        "f1_luar": {"lulus": True},
        "spesies_turun_recall": {"lulus": False},
        "test_penjaga": {"lulus": True},
    }
    # Tanpa pengecualian: gagal karena spesies_turun_recall tidak lulus.
    assert cek_gerbang(g) is False
    # Dengan pengecualian: kriteria itu dilewati, sisanya lulus.
    assert cek_gerbang(g, ["spesies_turun_recall"]) is True


def test_cek_gerbang_tidak_lewati_kriteria_lain():
    g = {
        "independen": {"lulus": True},
        "spesies_turun_recall": {"lulus": False},
        "test_penjaga": {"lulus": False},
    }
    # Pengecualian hanya melewati spesies_turun_recall; test_penjaga tetap gagal.
    assert cek_gerbang(g, ["spesies_turun_recall"]) is False
