"""Latih regresi logistik pada korpus v2 lalu simpan sebagai checkpoint runtime.

Alasan model ini dipilih: pada korpus v2 dan korpus lapangan yang sama, regresi
logistik mengalahkan MLP pada akurasi uji bersih (0,7638 lawan 0,7402), pada
rekaman ponsel (0,4934 lawan 0,4705), pada Xeno-canto berisik (0,7391 lawan
0,6734), dan yang terpenting pada deteksi palsu klip pengecoh (0,3828 lawan
0,5391). Model ini juga tidak butuh GPU.

Bentuk disimpan sebagai MLP dengan activation="linear", W2 identitas, dan
dropout 0, sehingga forward menghasilkan logits = X @ W1 + b1. Dengan begitu
mesin inferensi yang ada (ml/engines/embedding_clf.py) tidak perlu diubah sama
sekali, cukup memuat checkpoint ini.

Kalibrasi temperature dan bias per kelas dihitung dari split validasi, memakai
fungsi yang sama dengan pelatihan MLP supaya resep runtime identik.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sklearn.linear_model import LogisticRegression  # noqa: E402

from ml.train import MLP  # noqa: E402

_ap = argparse.ArgumentParser(description="Latih LogReg dan simpan sebagai checkpoint runtime")
_ap.add_argument("--emb-dir", default=str(ROOT / "ml/embeddings_v2"))
_ap.add_argument("--splits", default=str(ROOT / "ml/data/splits_v2.json"))
_ap.add_argument("--ckpt-in", default=str(ROOT / "ml/checkpoints_v2"),
                 help="sumber normalization.npz kalau --emb-dir tidak punya sendiri")
_ap.add_argument("--out-dir", default=str(ROOT / "ml/runs/logreg"))
_ap.add_argument("--report-dir", default=str(ROOT / "ml/reports_logreg"))
_ap.add_argument("--maks-negatif", type=int, default=3000)
_ap.add_argument("--seed", type=int, default=2024)
_ap.add_argument("--C", type=float, default=1.0)
_args = _ap.parse_args()

EMB = Path(_args.emb_dir)
CKPT_IN = Path(_args.ckpt_in)
CKPT_OUT = Path(_args.out_dir)
REPORTS_OUT = Path(_args.report_dir)
SPLITS = Path(_args.splits)
MAKS_NEGATIF = _args.maks_negatif
SEED = _args.seed
C = _args.C


def softmax(z):
    z = z - z.max(axis=1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


def nll(probs, y):
    return float(np.mean(-np.log(probs[np.arange(len(y)), y] + 1e-9)))


def latih_temperature(logits, y):
    """Temperature scaling: satu parameter, dioptimasi pada split validasi."""
    terbaik, nll_terbaik = 1.0, float("inf")
    for T in np.arange(0.05, 5.0, 0.005):
        nilai = nll(softmax(logits / T), y)
        if nilai < nll_terbaik:
            terbaik, nll_terbaik = float(T), nilai
    return terbaik, nll_terbaik


def latih_bias(logits, y, T, langkah=2000, lr=0.05):
    """Bias aditif per kelas untuk menyeimbangkan prior yang miring.

    Tanpa langkah ini, kelas negatif yang jumlahnya 3000 menarik probabilitas
    semua kelas target ke bawah dan tingkat deteksi ikut turun.

    Gradien NLL terhadap bias adalah rata-rata (probabilitas - one-hot) di
    seluruh sampel, jadi hasilnya vektor sepanjang jumlah kelas.
    """
    n_kelas = logits.shape[1]
    bias = np.zeros(n_kelas, dtype=np.float32)
    satu_panas = np.zeros((len(y), n_kelas), dtype=np.float32)
    satu_panas[np.arange(len(y)), y] = 1.0
    for _ in range(langkah):
        probs = softmax((logits + bias) / T)
        grad = ((probs - satu_panas).mean(axis=0)).astype(np.float32)
        bias -= lr * grad
    return bias


emb = np.load(EMB / "embeddings.npy")
lab = np.load(EMB / "labels.npy")
ids = json.load(open(EMB / "clip_ids.json"))
label_map = json.load(open(EMB / "label_map.json"))
sp = json.load(open(SPLITS))
idx = {c: i for i, c in enumerate(ids)}

rng = np.random.default_rng(SEED)
tr = [c for c in sp["train"] if c in idx]
tr_lab = np.array([lab[idx[c]] for c in tr])
neg = label_map["_negative"]
pos_neg = [i for i, c in enumerate(tr) if tr_lab[i] == neg]
if len(pos_neg) > MAKS_NEGATIF:
    buang = set(rng.choice(pos_neg, size=len(pos_neg) - MAKS_NEGATIF, replace=False).tolist())
    tr = [c for i, c in enumerate(tr) if i not in buang]
    tr_lab = np.array([label for i, label in enumerate(tr_lab) if i not in buang])

norm = np.load(CKPT_IN / "normalization.npz")
mean, std = norm["mean"], norm["std"]
Xtr = ((emb[[idx[c] for c in tr]] - mean) / std).astype(np.float32)

print(f"Melatih LogReg pada {Xtr.shape[0]} klip (negatif dibatasi {MAKS_NEGATIF})...")
lr = LogisticRegression(max_iter=3000, C=C, class_weight="balanced")
lr.fit(Xtr, tr_lab)

# Susun checkpoint dalam bentuk yang bisa dibaca mesin runtime.
n_kelas = len(label_map)
model = MLP(Xtr.shape[1], n_kelas, n_kelas, dropout=0.0, activation="linear")
model.W1 = np.ascontiguousarray(lr.coef_.T).astype(np.float32)
model.b1 = np.ascontiguousarray(lr.intercept_).astype(np.float32)
model.W2 = np.eye(n_kelas, dtype=np.float32)
model.b2 = np.zeros(n_kelas, dtype=np.float32)
model.training = False

val = [c for c in sp["val"] if c in idx]
Xval = ((emb[[idx[c] for c in val]] - mean) / std).astype(np.float32)
yval = lab[[idx[c] for c in val]]

logits_val = Xval @ model.W1 + model.b1
T, nll_T = latih_temperature(logits_val, yval)
nll_awal = nll(softmax(logits_val), yval)
bias = latih_bias(logits_val, yval, T)
nll_akhir = nll(softmax((logits_val + bias) / T), yval)
print(f"kalibrasi: T={T:.4f}  NLL {nll_awal:.4f} -> {nll_akhir:.4f} "
      f"({(1 - nll_akhir / nll_awal) * 100:.2f} persen)")

# Verifikasi forward harus sama dengan predict_proba sklearn sebelum disimpan.
probs_model = softmax((Xval @ model.W1 + model.b1) / 1.0)
probs_sklearn = lr.predict_proba(Xval)
selisih = float(np.max(np.abs(probs_model - probs_sklearn)))
print(f"selisih forward terhadap sklearn: {selisih:.8f}")
assert selisih < 1e-4, "checkpoint tidak mereproduksi prediksi sklearn"

CKPT_OUT.mkdir(parents=True, exist_ok=True)
REPORTS_OUT.mkdir(parents=True, exist_ok=True)
model.save(str(CKPT_OUT / "best_model.npz"), temperature=T, bias=bias)

# Normalisasi harus ikut, karena runtime membacanya dari direktori checkpoint.
np.savez(CKPT_OUT / "normalization.npz", mean=mean, std=std)
json.dump(label_map, open(CKPT_OUT / "label_map.json", "w"), indent=2)

# Ambang per spesies dari probabilitas validasi model ini sendiri.
probs_val = softmax((logits_val + bias) / T)
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
json.dump(ambang, open(REPORTS_OUT / "thresholds.json", "w"), indent=2)

def _rel(p: Path) -> str:
    """Jalur relatif dari ROOT, tahan terhadap path absolut maupun relatif."""
    p = p.resolve()
    try:
        return str(p.relative_to(ROOT.resolve()))
    except ValueError:
        return str(p)


json.dump({
    "jenis": "logistic_regression_multikelas",
    "C": C,
    "class_weight": "balanced",
    "maks_negatif": MAKS_NEGATIF,
    "seed": SEED,
    "jumlah_latih": int(Xtr.shape[0]),
    "temperature": T,
    "nll_sebelum_kalibrasi": nll_awal,
    "nll_sesudah_kalibrasi": nll_akhir,
    "epoch": 1,
    "best_val_acc": float(np.mean(np.argmax(probs_val, axis=1) == yval)),
    "emb_dir": _rel(EMB),
    "splits_file": _rel(SPLITS),
}, open(CKPT_OUT / "meta.json", "w"), indent=2)

print()
print(f"checkpoint : {CKPT_OUT / 'best_model.npz'}")
print(f"normalisasi: {CKPT_OUT / 'normalization.npz'}")
print(f"ambang     : {REPORTS_OUT / 'thresholds.json'}")
