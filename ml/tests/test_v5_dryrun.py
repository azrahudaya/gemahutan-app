"""Uji kering logika merge korpus v5 tanpa menyentuh artefak produksi.

Membuktikan: iNat dibuang dari train, val/uji tidak berubah, label negatif XC
memakai indeks _negative, jumlah klip cocok.
"""
import csv
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
import ml.siapkan_korpus_v5 as v5  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent.parent


def test_merge_v5(tmp_path: Path) -> None:
    neg = tmp_path / "neg"
    emb = tmp_path / "emb"
    ckpt = tmp_path / "ckpt"
    for d in (neg, emb, ckpt):
        d.mkdir(parents=True)

    # Embedding negatif XC palsu: 5 klip
    rng = np.random.default_rng(0)
    np.save(neg / "embeddings.npy", rng.standard_normal((5, 1024)).astype(np.float32))
    np.save(neg / "labels.npy", np.zeros(5, dtype=np.int32))
    json.dump([f"xc-90000{i}" for i in range(5)], open(neg / "clip_ids.json", "w"))
    json.dump({"_negative": 0}, open(neg / "label_map.json", "w"))

    man = tmp_path / "manifest_negatif_xc.csv"
    with open(man, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[
            "clip_id", "source", "source_url", "species_scientific",
            "species_common", "quality", "license", "author", "country",
            "duration_s", "local_path"])
        w.writeheader()
        for i in range(5):
            w.writerow({
                "clip_id": f"xc-90000{i}", "source": "xeno-canto",
                "source_url": f"https://xeno-canto.org/90000{i}",
                "species_scientific": "Test_sp", "species_common": "Test",
                "quality": "A",
                "license": "https://creativecommons.org/licenses/by-nc-sa/4.0/",
                "author": "X", "country": "Indonesia", "duration_s": "0:10",
                "local_path": f"negatif_xc/Test_sp/xc-90000{i}.mp3"})

    # Alihkan jalur keluar ke temp, no-op-kan ekstraksi
    v5.NEG_XC_MANIFEST = man
    v5.NEG_XC_MANIFEST_NONBURUNG = tmp_path / "tidak_ada.csv"
    v5.NEG_XC_EMB = neg
    v5.OUT_EMB = emb
    v5.OUT_SPLITS = tmp_path / "splits_v5.json"
    v5.OUT_MANIFEST = tmp_path / "manifest_v5.csv"
    v5.OUT_CKPT = ckpt
    v5.tulis_manifest_ekstraksi = lambda: 5
    v5.ekstrak_embeddings_negatif = lambda: None

    assert v5.main() == 0

    sp = json.load(open(tmp_path / "splits_v5.json"))
    sp3 = json.load(open(ROOT / "ml/data/splits_v3.json"))
    assert sp["test"] == sp3["test"], "split uji berubah"
    assert sp["val"] == sp3["val"], "split val berubah"
    assert not any(c.startswith("inat") for c in sp["train"]), "iNat masih di train"

    e = np.load(emb / "embeddings.npy")
    lab = np.load(emb / "labels.npy")
    ids = json.load(open(emb / "clip_ids.json"))
    assert e.shape[0] == 5151 + 5, f"jumlah salah: {e.shape[0]}"
    assert len(ids) == e.shape[0]
    assert (lab[-5:] == 25).all(), "label negatif XC bukan indeks _negative"
    assert (tmp_path / "normalization.npz").exists() or (ckpt / "normalization.npz").exists()