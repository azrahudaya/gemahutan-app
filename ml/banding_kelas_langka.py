"""Bandingkan dua checkpoint pada set uji independen, dengan embedding di-cache.

Kenapa skrip terpisah: klip set uji independen sengaja tidak ada di
ml/embeddings_v2 (memang bukan data latih), jadi embedding-nya harus dihitung
dari audio. Perhitungan itu lambat, jadi hasilnya di-cache ke disk sekali lalu
dipakai ulang untuk semua checkpoint yang dibandingkan.

Embedding disimpan BERSIH (belum dinormalisasi), karena tiap checkpoint punya
mean dan std-nya sendiri. Normalisasi baru diterapkan saat mengukur.
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

INDEP = ROOT / "ml/data/uji_independen"
CACHE = ROOT / "ml/data/uji_independen/embedding_cache"
LABEL_MAP = ROOT / "ml/embeddings_v2/label_map.json"
label_map = json.load(open(LABEL_MAP))


def hitung_cache() -> None:
    """Hitung embedding tiap jendela per berkas, simpan satu berkas .npz per klip."""
    CACHE.mkdir(parents=True, exist_ok=True)
    baris = [b for b in csv.DictReader(open(INDEP / "manifest.csv"))
             if b["species_scientific"] in label_map]
    interp = ef.ee.create_interpreter(ef.ee.get_birdnet_model_path())
    baru = 0
    for b in baris:
        tujuan = CACHE / f"{b['clip_id']}.npy"
        if tujuan.exists():
            continue
        berkas = INDEP / b["local_path"]
        if not berkas.exists():
            continue
        fitur, _ = ef.embed_folder(interp, [berkas], 8, "", verbose=False)
        if not len(fitur):
            continue
        np.save(tujuan, fitur)
        baru += 1
    print(f"cache embedding: {baru} berkas baru, total {len(list(CACHE.glob('*.npy')))}")


def muat_cache():
    """Kembalikan daftar (clip_id, kelas, embedding semua jendela)."""
    hasil = []
    kelas_per_clip = {}
    with (INDEP / "manifest.csv").open() as fh:
        for r in csv.DictReader(fh):
            if r["species_scientific"] in label_map:
                kelas_per_clip[r["clip_id"]] = label_map[r["species_scientific"]]
    for f in sorted(CACHE.glob("*.npy")):
        cid = f.stem
        if cid not in kelas_per_clip:
            continue
        hasil.append((cid, kelas_per_clip[cid], np.load(f)))
    return hasil


def ukur(ckpt_dir: Path, data) -> dict:
    from ml.model_loader import muat

    model, mean, std = muat(ckpt_dir)
    assert not model.training, f"dropout masih hidup di {ckpt_dir}"

    benar_semua, benar_pertama, benar_yakin = [], [], []
    for _cid, kelas, feats in data:
        X = ((feats - mean) / std).astype(np.float32)
        probs = model.forward(X)
        pred = np.argmax(probs, axis=1)
        benar_semua.extend(bool(p == kelas) for p in pred)
        benar_pertama.append(bool(pred[0] == kelas))
        benar_yakin.append(bool(pred[int(np.argmax(probs.max(axis=1)))] == kelas))

    def rangkum(v):
        v = np.array(v)
        acc = float(np.mean(v))
        g = 1.96 * float(np.sqrt(acc * (1 - acc) / len(v)))
        return {"n": int(len(v)), "akurasi": acc,
                "ic95": [max(0.0, acc - g), min(1.0, acc + g)]}

    return {
        "checkpoint": str(ckpt_dir),
        "semua_jendela": rangkum(benar_semua),
        "jendela_pertama": rangkum(benar_pertama),
        "jendela_paling_yakin": rangkum(benar_yakin),
    }


if __name__ == "__main__":
    hitung_cache()
    data = muat_cache()
    print(f"klip terpakai: {len(data)}, jendela: {sum(len(f) for _, _, f in data)}")
    print()
    hasil = []
    for d in (ROOT / "ml/checkpoints",
              ROOT / "ml/checkpoints_logreg_langka",
              ROOT / "ml/checkpoints_logreg_v3"):
        if not (d / "best_model.npz").exists():
            print(f"lewat (tidak ada): {d}")
            continue
        h = ukur(d, data)
        hasil.append(h)
        print(f"{d.name}")
        for kunci in ("semua_jendela", "jendela_pertama", "jendela_paling_yakin"):
            r = h[kunci]
            print(f"   {kunci:22s} n={r['n']:4d}  acc {r['akurasi']:.4f}  "
                  f"(95%: {r['ic95'][0]:.4f} sampai {r['ic95'][1]:.4f})")
        print()
    json.dump(hasil, open(ROOT / "ml/reports_v2/banding_kelas_langka.json", "w"), indent=2)
    print("tersimpan: ml/reports_v2/banding_kelas_langka.json")
