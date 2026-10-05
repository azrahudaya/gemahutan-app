"""Gabungkan embedding kelas langka, latih ulang model, lalu ukur pada set independen.

Latar: enam kelas punya klip paling sedikit dan beberapa recall-nya nol. Dicrurus
macrocercus hanya 17 klip latih. Panen tambahan memberi 98 klip baru untuk kelas
langka (Dicrurus macrocercus +12, Gallus gallus +12, dan seterusnya).

Skrip ini:
1. Menggabungkan ml/embeddings_v2 dengan ml/embeddings_langka, memetakan ulang
   indeks kelas lewat NAMA spesies (label_map kedua berkas berbeda indeksnya).
2. Menghitung ulang normalisasi dari gabungan data latih saja.
3. Melatih LogReg dengan konfigurasi yang sama seperti model yang dipakai.
4. Mengukur pada dua set: split uji lama 127 klip dan set uji independen 135
   klip, supaya perbandingannya sebanding dengan model yang sekarang terpasang.

Hasil ditulis ke ml/checkpoints_logreg_langka. Model yang terpasang TIDAK
ditimpa sebelum angkanya terbukti lebih baik.
"""
import csv
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.metrics import accuracy_score, f1_score, recall_score  # noqa: E402

V2 = ROOT / "ml/embeddings_v2"
LANGKA = ROOT / "ml/embeddings_langka"
CKPT_V2 = ROOT / "ml/checkpoints_v2"
OUT = ROOT / "ml/runs/logreg_langka"
SPLITS = ROOT / "ml/data/splits_v2.json"
INDEP = ROOT / "ml/data/uji_independen"
MAKS_NEGATIF = 3000
SEED = 2024


def softmax(z):
    z = z - z.max(axis=1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


# 1. Gabungkan, memetakan indeks kelas lewat nama spesies.
emb2 = np.load(V2 / "embeddings.npy")
lab2 = np.load(V2 / "labels.npy")
ids2 = json.load(open(V2 / "clip_ids.json"))
lm2 = json.load(open(V2 / "label_map.json"))
inv2 = {v: k for k, v in lm2.items()}

emb3 = np.load(LANGKA / "embeddings.npy")
lab3 = np.load(LANGKA / "labels.npy")
ids3 = json.load(open(LANGKA / "clip_ids.json"))
lm3 = json.load(open(LANGKA / "label_map.json"))

# Buang klip yang clip_id-nya sudah ada (harusnya kosong, ini jaring pengaman).
sudah = set(ids2)
jaga = [i for i, c in enumerate(ids3) if c not in sudah]
print(f"kelas langka: {len(ids3)} klip, dipakai {len(jaga)}")

inv3 = {v: k for k, v in lm3.items()}
lab3_remap = np.array([lm2[inv3[int(lab3[i])]] for i in jaga], dtype=lab3.dtype)
emb3_pakai = emb3[jaga]
ids3_pakai = [ids3[i] for i in jaga]

emb = np.vstack([emb2, emb3_pakai]).astype(np.float32)
lab = np.concatenate([lab2, lab3_remap])
ids = ids2 + ids3_pakai
print(f"gabungan: {emb.shape[0]} klip, dimensi {emb.shape[1]}, {len(lm2)} kelas")

# 2. Normalisasi dari data latih gabungan saja.
sp = json.load(open(SPLITS))
idx = {c: i for i, c in enumerate(ids)}
tr = [idx[c] for c in sp["train"] if c in idx]
# Klip baru yang belum ada di split manapun masuk ke latih, bukan ke uji.
di_split = set(sp["train"]) | set(sp["val"]) | set(sp["test"])
baru = [idx[c] for c in ids3_pakai if c not in di_split]
tr = tr + baru
print(f"latih: {len(tr)} klip ({len(baru)} klip baru dari kelas langka)")

mean = emb[tr].mean(axis=0).astype(np.float32)
std = emb[tr].std(axis=0).astype(np.float32)
std[std < 1e-8] = 1.0

# 3. Latih, dengan negatif dibatasi sama seperti model yang dipakai.
rng = np.random.default_rng(SEED)
kelas_neg = lm2["_negative"]
ytr_all = lab[tr]
pos_neg = [i for i, v in enumerate(tr) if ytr_all[i] == kelas_neg]
jaga_neg = set(rng.choice(pos_neg, size=max(0, len(pos_neg) - MAKS_NEGATIF), replace=False).tolist())
tr_pakai = [v for i, v in enumerate(tr) if i not in jaga_neg]
print(f"latih setelah negatif dibatasi {MAKS_NEGATIF}: {len(tr_pakai)}")

Xtr = ((emb[tr_pakai] - mean) / std).astype(np.float32)
lr = LogisticRegression(max_iter=3000, C=1.0, class_weight="balanced")
lr.fit(Xtr, lab[tr_pakai])


def ukur(nama, berkas_ids, berkas_lab):
    sel = [idx[c] for c in berkas_ids if c in idx]
    if not sel:
        print(f"  {nama:28s} tidak ada klip di embedding gabungan (memang di luar data latih)")
        return None
    y = np.array([berkas_lab[c] for c in berkas_ids if c in idx])
    X = ((emb[sel] - mean) / std).astype(np.float32)
    p = lr.predict(X)
    acc = float(accuracy_score(y, p))
    galat = 1.96 * float(np.sqrt(acc * (1 - acc) / len(y)))
    f1 = float(f1_score(y, p, average="macro", zero_division=0))
    rec = float(recall_score(y, p, labels=[kelas_neg], average="micro", zero_division=0))
    print(f"  {nama:28s} n={len(y):4d}  acc {acc:.4f} (95%: {max(0, acc - galat):.4f} "
          f"sampai {min(1, acc + galat):.4f})  f1 {f1:.4f}  recall_neg {rec:.4f}")
    return {"n": len(y), "akurasi": acc, "ic95": [max(0, acc - galat), min(1, acc + galat)],
            "f1_makro": f1, "recall_negatif": rec}


print()
print("=== SPLIT UJI LAMA (127 klip Xeno-canto) ===")
te = [c for c in sp["test"] if c in idx]
lab_by_id = {c: int(lab[idx[c]]) for c in ids}
hasil_lama = ukur("uji 127 klip", te, lab_by_id)

print()
print("=== SET UJI INDEPENDEN (tidak pernah dilatih) ===")
ind_ids, ind_lab = [], {}
with (INDEP / "manifest.csv").open() as fh:
    for r in csv.DictReader(fh):
        cid = r["clip_id"]
        if cid in idx:
            ind_ids.append(cid)
            ind_lab[cid] = int(lab[idx[cid]])
hasil_ind = ukur("uji independen", ind_ids, ind_lab)

# 4. Recall per kelas langka pada set uji LAMA, sebagai pemeriksaan cepat.
print()
print("=== RECALL KELAS LANGKA pada split uji lama ===")
sel = [idx[c] for c in te if c in idx]
y = np.array([lab_by_id[c] for c in te if c in idx])
X = ((emb[sel] - mean) / std).astype(np.float32)
p = lr.predict(X)
for nama in ("Dicrurus macrocercus", "Gallus gallus", "Chalcophaps indica",
             "Arachnothera longirostra"):
    k = lm2[nama]
    benar = y == k
    if benar.sum() == 0:
        print(f"  {nama:28s} tidak ada klip di split uji lama")
        continue
    rec = float(np.mean(p[benar] == k))
    print(f"  {nama:28s} recall {rec:.4f} dari {int(benar.sum())} klip")

OUT.mkdir(parents=True, exist_ok=True)
np.savez(OUT / "normalization.npz", mean=mean, std=std)
json.dump(lm2, open(OUT / "label_map.json", "w"), indent=2)
json.dump({
    "jenis": "logistic_regression_multikelas",
    "kelas_langka_ditambah": len(baru),
    "jumlah_latih": len(tr_pakai),
    "uji_127": hasil_lama,
    "uji_independen": hasil_ind,
    "pembanding_terpasang": {"uji_127": 0.7874, "uji_independen_terpasang": 0.6412},
}, open(OUT / "meta.json", "w"), indent=2)

# Simpan model dalam bentuk checkpoint yang bisa dibaca mesin runtime.
n_kelas = len(lm2)
from ml.train import MLP  # noqa: E402

m = MLP(emb.shape[1], n_kelas, n_kelas, dropout=0.0, activation="linear")
m.W1 = np.ascontiguousarray(lr.coef_.T).astype(np.float32)
m.b1 = np.ascontiguousarray(lr.intercept_).astype(np.float32)
m.W2 = np.eye(n_kelas, dtype=np.float32)
m.b2 = np.zeros(n_kelas, dtype=np.float32)
m.training = False
m.save(str(OUT / "best_model.npz"))

print()
print(f"tersimpan: {OUT}")
