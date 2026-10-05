"""Ukur set uji independen dengan cara yang SEBANDING dengan split uji lama.

Masalah yang diperbaiki: `evaluate_field.jendela_audio` memotong berkas jadi
sampai 8 jendela 3 detik dan memberi SEMUA jendela label spesies berkas itu.
Pada rekaman Xeno-canto yang panjangnya puluhan detik, burungnya tidak berbunyi
sepanjang rekaman, jadi jendela tanpa burung ikut dihitung salah. Split uji lama
(127 klip) memakai 1 jendela per klip, jadi angka multi-jendela tidak sebanding
dan terlihat jauh lebih buruk dari sebenarnya (0,4833 lawan 0,7874).

Skrip ini mengukur tiga cara supaya bedanya terlihat:
1. satu jendela pertama per berkas,
2. satu jendela terbaik per berkas (maksimum keyakinan), meniru cara pemakaian
   nyata di lapangan di mana deteksi diambil dari jendela paling yakin,
3. semua jendela, sama seperti pengukuran sebelumnya, sebagai pembanding.
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

TUJUAN = ROOT / "ml/data/uji_independen"
CKPT = ROOT / "ml/checkpoints"

label_map = json.load(open(ROOT / "ml/embeddings_v2/label_map.json"))
norm = np.load(CKPT / "normalization.npz")
mean, std = norm["mean"], norm["std"]
model, _, _ = muat(CKPT)

baris = [b for b in csv.DictReader(open(TUJUAN / "manifest.csv"))
         if b["species_scientific"] in label_map]
interp = ef.ee.create_interpreter(ef.ee.get_birdnet_model_path())

per_berkas = []
for b in baris:
    berkas = TUJUAN / b["local_path"]
    if not berkas.exists():
        continue
    fitur, _ = ef.embed_folder(interp, [berkas], 8, "", verbose=False)
    if not len(fitur):
        continue
    probs = ef.tebak(model, fitur, mean, std, len(label_map))
    per_berkas.append({
        "clip_id": b["clip_id"],
        "kelas": label_map[b["species_scientific"]],
        "probs": probs,
    })

print(f"berkas terpakai: {len(per_berkas)}")
n_jendela = sum(len(x["probs"]) for x in per_berkas)
print(f"total jendela: {n_jendela}")
print()


def lapor(nama, benar):
    n = len(benar)
    acc = float(np.mean(benar))
    galat = 1.96 * float(np.sqrt(acc * (1 - acc) / n)) if n else 0.0
    print(f"  {nama:44s} n={n:4d}  akurasi {acc:.4f}  "
          f"(95%: {max(0, acc - galat):.4f} sampai {min(1, acc + galat):.4f})")
    return acc


print("=== HASIL, tiga cara pengukuran ===")
benar_semua = np.array([
    bool(p) for x in per_berkas
    for p in (np.argmax(x["probs"], axis=1) == x["kelas"])
])
lapor("1) semua jendela (pengukuran lama)", benar_semua)
lapor("2) jendela pertama per berkas", np.array(
    [bool(np.argmax(x["probs"][0]) == x["kelas"]) for x in per_berkas]
))
lapor("3) jendela paling yakin per berkas", np.array(
    [bool(np.argmax(x["probs"][int(np.argmax(x["probs"].max(axis=1)))]) == x["kelas"])
     for x in per_berkas]
))

print()
print("pembanding split uji lama (127 klip, 1 jendela per klip): 0,7874")
