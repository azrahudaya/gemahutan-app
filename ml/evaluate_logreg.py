"""Evaluasi lapangan untuk kandidat LogisticRegression, memakai jalur yang sama
dengan ml/evaluate_field.py (jendela audio, metrik, deteksi palsu).

Alasan skrip ini ada: di split uji bersih, LogReg C=1 class_weight balanced
memberi akurasi 0,7638 dan F1 0,6925 dengan recall negatif 0,9474, sedangkan MLP
yang ada memberi 0,7402 dan 0,6764 dengan recall negatif yang sama persis. Tapi
metrik penentu keputusan deploy adalah deteksi palsu pada klip pengecoh di
lapangan, dan itu belum pernah diukur untuk LogReg.

Ambang per spesies dihitung ulang dari probabilitas validasi LogReg sendiri,
karena memakai ambang milik MLP akan menghukum atau menguntungkan LogReg secara
tidak adil.
"""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path.home() / "Projects" / "gemahutan"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "ml"))

import evaluate_field as ef  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.metrics import accuracy_score, f1_score, recall_score  # noqa: E402

EMB = ROOT / "ml/embeddings_v2"
CKPT = ROOT / "ml/checkpoints_v2"
SPLITS = ROOT / "ml/data/splits_v2.json"
MAKS_NEGATIF = 3000
SEED = 2024

emb = np.load(EMB / "embeddings.npy")
lab = np.load(EMB / "labels.npy")
ids = json.load(open(EMB / "clip_ids.json"))
label_map = json.load(open(EMB / "label_map.json"))
inv_map = {v: k for k, v in label_map.items()}
sp = json.load(open(SPLITS))
idx = {c: i for i, c in enumerate(ids)}
kelas_neg = label_map["_negative"]

rng = np.random.default_rng(SEED)
tr = [c for c in sp["train"] if c in idx]
tr_lab = np.array([lab[idx[c]] for c in tr])
pos_neg = [i for i, c in enumerate(tr) if tr_lab[i] == kelas_neg]
if len(pos_neg) > MAKS_NEGATIF:
    buang = set(rng.choice(pos_neg, size=len(pos_neg) - MAKS_NEGATIF, replace=False).tolist())
    tr = [c for i, c in enumerate(tr) if i not in buang]
    tr_lab = np.array([label for i, label in enumerate(tr_lab) if i not in buang])

norm = np.load(CKPT / "normalization.npz")
mean, std = norm["mean"], norm["std"]
Xtr = ((emb[[idx[c] for c in tr]] - mean) / std).astype(np.float32)

print(f"Melatih LogReg pada {Xtr.shape[0]} klip...")
lr = LogisticRegression(max_iter=3000, C=1.0, class_weight="balanced")
lr.fit(Xtr, tr_lab)

# Ambang LogReg sendiri, dihitung dari split validasi.
val = [c for c in sp["val"] if c in idx]
Xval = ((emb[[idx[c] for c in val]] - mean) / std).astype(np.float32)
yval = lab[[idx[c] for c in val]]
probs_val = lr.predict_proba(Xval)
ambang = {}
for nama, kelas in label_map.items():
    skor = probs_val[:, kelas]
    positif = yval == kelas
    if positif.sum() == 0:
        ambang[nama] = 0.5
        continue
    kandidat = np.unique(np.concatenate([skor, [0.0, 1.0]]))
    terbaik, f1_terbaik = 0.5, -1.0
    for t in kandidat:
        pred = skor >= t
        if pred.sum() == 0:
            continue
        tp = np.sum(pred & positif)
        fp = np.sum(pred & ~positif)
        fn = np.sum(~pred & positif)
        f1 = 2 * tp / (2 * tp + fp + fn) if (2 * tp + fp + fn) else 0.0
        if f1 > f1_terbaik:
            terbaik, f1_terbaik = float(t), f1
    ambang[nama] = terbaik

# Uji bersih
te = [c for c in sp["test"] if c in idx]
Xte = ((emb[[idx[c] for c in te]] - mean) / std).astype(np.float32)
yte = lab[[idx[c] for c in te]]
probs_te = lr.predict_proba(Xte)
pred_te = np.argmax(probs_te, axis=1)
print()
print("=== UJI BERSIH (127 klip) ===")
print(f"  akurasi {accuracy_score(yte, pred_te):.4f}  f1 makro {f1_score(yte, pred_te, average='macro', zero_division=0):.4f}"
      f"  recall negatif {recall_score(yte, pred_te, labels=[kelas_neg], average='micro', zero_division=0):.4f}")

# Korpus lapangan: jalur yang sama dengan evaluate_field.py
print()
print("=== KORPUS LAPANGAN ===")
interp = ef.ee.create_interpreter(ef.ee.get_birdnet_model_path())
grups, _ = ef.kelompok_lapangan()
kelas_target = [c for c, nama in inv_map.items() if not nama.startswith("_")]
hasil = {}
for nama_grup, berkas_list in sorted(grups.items()):
    X_bagian, y_bagian = [], []
    terbaca = 0
    for berkas_satu in berkas_list:
        # Spesies sebenarnya diambil dari nama folder induk, sama seperti
        # ml/evaluate_field.py. Nama berkas tidak memuat label.
        kelas = label_map.get(berkas_satu.parent.name.replace("_", " "), -1)
        if kelas < 0 and nama_grup != "other":
            continue
        fitur_satu, _ = ef.embed_folder(interp, [berkas_satu], 8, "", verbose=False)
        if not len(fitur_satu):
            continue
        terbaca += 1
        X_bagian.append(fitur_satu)
        if kelas >= 0:
            y_bagian.append(np.full(len(fitur_satu), kelas, dtype=int))

    if not X_bagian:
        print(f"  {nama_grup}: tidak ada jendela terbaca")
        continue
    X = np.vstack(X_bagian)
    y = np.concatenate(y_bagian) if y_bagian else np.array([], dtype=int)
    Xn = ((X - mean) / std).astype(np.float32)
    probs = lr.predict_proba(Xn)

    if nama_grup == "other":
        palsu = ef.deteksi_palsu(probs, inv_map, ambang, kelas_target)
        print(f"  {nama_grup:12s} deteksi_palsu {palsu:.4f}  jendela {len(X)}  berkas terbaca {terbaca}")
        hasil[nama_grup] = {"deteksi_palsu": float(palsu), "jumlah_jendela": int(len(X))}
        continue
    m = ef.metrik(y, probs, inv_map, ambang, kelas_target)
    m["berkas_terbaca"] = terbaca
    print(f"  {nama_grup:12s} akurasi {m['akurasi_top1']:.4f}  f1 {m['macro_f1']:.4f}  "
          f"jendela {m['jumlah_jendela']}  berkas terbaca {terbaca}")
    hasil[nama_grup] = m

kal = CKPT / "reports_logreg.json"
Path(kal).write_text(json.dumps({
    "model": "LogReg C=1 class_weight=balanced, korpus v2",
    "uji_bersih": {
        "akurasi": float(accuracy_score(yte, pred_te)),
        "f1_makro": float(f1_score(yte, pred_te, average="macro", zero_division=0)),
        "recall_negatif": float(recall_score(yte, pred_te, labels=[kelas_neg], average="micro", zero_division=0)),
    },
    "lapangan": hasil,
}, indent=2))
print()
print(f"tersimpan: {kal}")
