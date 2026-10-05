"""Test: daftar spesies TARGET berasal dari species_list.json, bukan dari label_map.

Bug yang dijaga (ditemukan 2 Oktober 2026 saat menyiapkan K4, SEBELUM modelnya
dilatih): CascadeEngine menyusun `_indonesian_species` dari seluruh kunci
label_map minus `_negative` (cascade.py baris 91 versi lama). K4 menambahkan
kelas PEMICU yang justru harus diperlakukan NON-target ("prediksi ke kelas
pemicu = non-target", ML_10 K4). Dengan versi lama, menambah kelas pemicu
membuat engine melaporkannya sebagai deteksi target, yaitu kebalikan dari maksud
K4. Akibatnya deteksi palsu NAIK tanpa ada yang salah di modelnya, dan sebabnya
tidak akan kelihatan dari angkanya saja.

Diuji lewat fungsi `daftar_spesies_target` yang sesungguhnya dipakai engine,
BUKAN dengan meniru logikanya di dalam test. Versi pertama test ini meniru
logikanya (membaca ulang species_list.json) sehingga akan tetap lulus walaupun
kode engine-nya salah, jadi test itu tidak menguji apa pun.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

ML = ROOT / "ml"

from ml.engines.cascade import daftar_spesies_target  # noqa: E402

PEMICU_K4 = ["Accipiter_badius", "Centropus_sinensis", "Orthotomus_ruficeps"]


def _species_list() -> set[str]:
    return {e["scientific_name"] for e in json.loads((ML / "data" / "species_list.json").read_text())}


def test_label_map_produksi_sama_dengan_species_list():
    """Pengaman no-op: kalau gagal, perilaku produksi BERUBAH, bukan cuma refactor."""
    lm = json.loads((ML / "checkpoints" / "label_map.json").read_text())
    dari_label_map = {k for k in lm if k != "_negative"}
    sl = _species_list()
    assert dari_label_map == sl, (
        f"selisih: hanya di label_map {sorted(dari_label_map - sl)}, "
        f"hanya di species_list {sorted(sl - dari_label_map)}"
    )
    assert len(sl) == 25


def test_kelas_pemicu_tidak_jadi_target():
    """Kelas pemicu K4 di label_map tidak boleh masuk daftar spesies target."""
    label_map = dict.fromkeys(_species_list(), 0)
    label_map["_negative"] = 25
    for i, sp in enumerate(PEMICU_K4):
        label_map[sp] = 26 + i

    target = daftar_spesies_target(label_map)

    for sp in PEMICU_K4:
        assert sp in label_map, "prasyarat test: kelas pemicu ada di label_map"
        assert sp not in target, f"kelas pemicu {sp} TIDAK boleh jadi spesies target"
    assert target == _species_list()
    assert len(target) == 25


def test_jalur_cadangan_kalau_species_list_hilang(monkeypatch, tmp_path):
    """Tanpa species_list.json, engine jatuh ke label_map supaya tetap jalan."""
    from ml.engines import cascade as mod

    monkeypatch.setattr(mod, "ML_DIR", tmp_path)
    label_map = {"Passer montanus": 0, "Cinnyris jugularis": 1, "_negative": 2}
    assert daftar_spesies_target(label_map) == {"Passer montanus", "Cinnyris jugularis"}
