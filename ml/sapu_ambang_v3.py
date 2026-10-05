"""Setel ambang spesies target pada model v3: kurva trade-off deteksi lawan deteksi palsu.

Koreksi penting: deteksi palsu pada klip pengecoh BUKAN dikendalikan ambang
`_negative`, melainkan ambang tiap spesies target. `deteksi_palsu()` menghitung
bagian jendela pengecoh yang punya minimal satu kelas target di atas ambangnya
sendiri. Ambang `_negative` tidak masuk perhitungan itu sama sekali.

Median ambang target v3 hanya 0,15, jadi wajar banyak pengecoh lolos. Skrip ini
menyapu pengali ambang dan mengukur akibatnya pada tiga hal sekaligus:

1. deteksi palsu pada 118 klip pengecoh,
2. tingkat deteksi pada set uji independen (apakah burungnya masih terdeteksi),
3. akurasi argmax pada set independen (tidak terpengaruh ambang, sebagai kontrol).

Embedding pengecoh di-cache ke disk karena perhitungannya lambat.
"""
import csv
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "ml"))
sys.path.insert(0, str(ROOT / "ml" / "data"))

import evaluate_field as ef  # noqa: E402

from ml.model_loader import muat  # noqa: E402

CKPT = ROOT / "ml/checkpoints"
INDEP_CACHE = ROOT / "ml/data/uji_independen/embedding_cache"
DECOY_CACHE = ROOT / "ml/data/field/embedding_cache_pengecoh"
AUDIO_OTHER = ROOT / "ml/data/field/audio/other"
label_map = json.load(open(ROOT / "ml/embeddings_v3/label_map.json"))
inv = {v: k for k, v in label_map.items()}
kelas_target = [c for c, n in inv.items() if not n.startswith("_")]


def cache_pengecoh() -> None:
    """Simpan embedding tiap berkas pengecoh, satu .npy per berkas."""
    DECOY_CACHE.mkdir(parents=True, exist_ok=True)
    berkas = sorted(AUDIO_OTHER.rglob("*"))
    berkas = [b for b in berkas if b.suffix.lower() in (".mp3", ".wav", ".flac", ".ogg", ".m4a", ".aac")]
    baru = 0
    if not berkas:
        print(f"tidak ada audio pengecoh di {AUDIO_OTHER}")
        return
    interp = ef.ee.create_interpreter(ef.ee.get_birdnet_model_path())
    for b in berkas:
        tujuan = DECOY_CACHE / f"{b.stem}.npy"
        if tujuan.exists():
            continue
        fitur, _ = ef.embed_folder(interp, [b], 8, "", verbose=False)
        if not len(fitur):
            continue
        np.save(tujuan, fitur)
        baru += 1
    print(f"cache pengecoh: {baru} berkas baru, total {len(list(DECOY_CACHE.glob('*.npy')))}")


cache_pengecoh()

model, mean, std = muat(CKPT)
assert not model.training
ambang_dasar = json.load(open(ROOT / "ml/reports/thresholds.json"))


def probs_of(feats):
    X = ((feats - mean) / std).astype(np.float32)
    return model.forward(X)


# Siapkan data sekali.
indep = []
for f in sorted(INDEP_CACHE.glob("*.npy")):
    indep.append((f.stem, np.load(f)))
decoy = [np.load(f) for f in sorted(DECOY_CACHE.glob("*.npy"))]

kelas_per_clip = {}
with (ROOT / "ml/data/uji_independen/manifest.csv").open() as fh:
    for r in csv.DictReader(fh):
        if r["species_scientific"] in label_map:
            kelas_per_clip[r["clip_id"]] = label_map[r["species_scientific"]]

print(f"set independen: {len(indep)} berkas, pengecoh: {len(decoy)} berkas")
print()
print(f"{'pengali':>8} {'deteksi palsu':>14} {'deteksi indep':>14} {'akurasi indep':>14}")
print("-" * 56)

hasil = []
for pengali in (1.0, 1.5, 2.0, 3.0, 4.0, 6.0, 8.0):
    ambang = {k: min(0.99, v * pengali) for k, v in ambang_dasar.items()}
    vektor = np.array([ambang.get(inv[c], 0.5) for c in range(len(label_map))])
    topeng = np.zeros(len(label_map), dtype=bool)
    topeng[kelas_target] = True

    # Deteksi palsu pada pengecoh.
    palsu = []
    for feats in decoy:
        p = probs_of(feats)
        palsu.extend(bool(v) for v in np.any((p >= vektor) & topeng, axis=1))
    fp = float(np.mean(palsu)) if palsu else 0.0

    # Deteksi dan akurasi pada set independen.
    det, benar = [], []
    for cid, feats in indep:
        if cid not in kelas_per_clip:
            continue
        p = probs_of(feats)
        k = kelas_per_clip[cid]
        det.extend(bool(v) for v in np.any((p >= vektor) & topeng, axis=1))
        # Jendela paling yakin, seperti cara pemakaian nyata.
        terbaik = int(np.argmax(p.max(axis=1)))
        benar.append(bool(np.argmax(p[terbaik]) == k))
    dr = float(np.mean(det)) if det else 0.0
    acc = float(np.mean(benar)) if benar else 0.0
    print(f"{pengali:>8.1f} {fp:>14.4f} {dr:>14.4f} {acc:>14.4f}")
    hasil.append({"pengali": pengali, "deteksi_palsu": fp, "deteksi_independen": dr,
                  "akurasi_independen": acc})

json.dump(hasil, open(ROOT / "ml/reports_v2/sapu_ambang_v3.json", "w"), indent=2)
print()
print("tersimpan: ml/reports_v2/sapu_ambang_v3.json")
