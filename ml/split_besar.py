"""Bagi ulang korpus v2 dengan split uji besar, lalu ukur dengan selang kepercayaan.

Masalah yang diperbaiki: split uji korpus v2 hanya 127 klip dari 8258, jadi satu
klip menggeser akurasi sekitar 0,8 poin. Angka sekecil itu tidak cukup untuk
mengklaim perbaikan, sama seperti masalah kelompok pengecoh yang hanya 21 berkas.

Skrip ini:
1. Membuat split baru yang stratified: 70 persen latih, 15 persen validasi,
   15 persen uji.
2. Melatih konfigurasi yang sama dengan model yang dipakai (LogReg C=1,
   class_weight balanced, negatif dibatasi 3000).
3. Mengukur akurasi pada split uji besar plus selang kepercayaan 95 persen
   (normal approximation), dan F1 makro.
4. Menjalankan 5-fold stratified cross-validation sebagai pembanding yang tidak
   bergantung pada satu pembagian.

Split lama TIDAK ditimpa. Hasilnya ditulis ke berkas terpisah supaya angka
kanonik yang sekarang tetap bisa dibandingkan.
"""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.metrics import accuracy_score, f1_score, recall_score  # noqa: E402
from sklearn.model_selection import StratifiedKFold, train_test_split  # noqa: E402

EMB = ROOT / "ml/embeddings_v2"
CKPT = ROOT / "ml/checkpoints_v2"
SPLITS_BARU = ROOT / "ml/data/splits_v2_besar.json"
LAPORAN = ROOT / "ml/reports_v2/split_besar.json"
MAKS_NEGATIF = 3000
SEED = 2024
C = 1.0


def bagi_negatif(idx_neg, maks, rng):
    """Batasi jumlah negatif, sama seperti pelatihan model yang dipakai."""
    if len(idx_neg) <= maks:
        return idx_neg
    return sorted(rng.choice(idx_neg, size=maks, replace=False).tolist())


def selang95(akurasi, n):
    """Selang kepercayaan 95 persen untuk proporsi (normal approximation)."""
    galat = 1.96 * float(np.sqrt(akurasi * (1 - akurasi) / n))
    return max(0.0, akurasi - galat), min(1.0, akurasi + galat)


emb = np.load(EMB / "embeddings.npy")
lab = np.load(EMB / "labels.npy")
ids = json.load(open(EMB / "clip_ids.json"))
label_map = json.load(open(EMB / "label_map.json"))
kelas_neg = label_map["_negative"]
inv = {v: k for k, v in label_map.items()}
norm = np.load(CKPT / "normalization.npz")
mean, std = norm["mean"], norm["std"]

n = len(ids)
print(f"korpus: {n} klip, {len(label_map)} kelas")

# Split stratified: 70/15/15.
idx_semua = np.arange(n)
idx_sisa, idx_test = train_test_split(
    idx_semua, test_size=0.15, random_state=SEED, stratify=lab
)
idx_train, idx_val = train_test_split(
    idx_sisa, test_size=0.15 / 0.85, random_state=SEED, stratify=lab[idx_sisa]
)
print(f"split baru: latih {len(idx_train)}, val {len(idx_val)}, uji {len(idx_test)}")

json.dump({
    "train": [ids[i] for i in idx_train],
    "val": [ids[i] for i in idx_val],
    "test": [ids[i] for i in idx_test],
    "catatan": "split stratified 70/15/15 dengan seed 2024, dibuat oleh ml/split_besar.py",
}, open(SPLITS_BARU, "w"), indent=2)

# Batasi negatif hanya di latih, sesuai konfigurasi model yang dipakai.
rng = np.random.default_rng(SEED)
pos_neg = [i for i in idx_train if lab[i] == kelas_neg]
jaga = set(bagi_negatif(list(pos_neg), MAKS_NEGATIF, rng))
idx_train_pakai = np.array([i for i in idx_train if lab[i] != kelas_neg or i in jaga])
print(f"latih setelah negatif dibatasi {MAKS_NEGATIF}: {len(idx_train_pakai)}")


def latih_dan_ukur(tr_idx, te_idx, label=""):
    Xtr = ((emb[tr_idx] - mean) / std).astype(np.float32)
    Xte = ((emb[te_idx] - mean) / std).astype(np.float32)
    ytr, yte = lab[tr_idx], lab[te_idx]
    lr = LogisticRegression(max_iter=3000, C=C, class_weight="balanced")
    lr.fit(Xtr, ytr)
    p = lr.predict(Xte)
    acc = float(accuracy_score(yte, p))
    f1 = float(f1_score(yte, p, average="macro", zero_division=0))
    neg = float(recall_score(yte, p, labels=[kelas_neg], average="micro", zero_division=0))
    lo, hi = selang95(acc, len(yte))
    print(f"  {label:22s} n={len(yte):5d}  acc {acc:.4f} (95%: {lo:.4f} sampai {hi:.4f})  "
          f"f1 {f1:.4f}  recall_neg {neg:.4f}")
    return {"n": int(len(yte)), "akurasi": acc, "ic95": [lo, hi], "f1_makro": f1,
            "recall_negatif": neg}


print()
print("=== uji pada split besar ===")
hasil_besar = latih_dan_ukur(idx_train_pakai, idx_test, "uji 15 persen")

print()
print("=== 5-fold stratified cross-validation ===")
skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)
accs, f1s = [], []
for k, (tr, te) in enumerate(skf.split(emb, lab), 1):
    Xtr = ((emb[tr] - mean) / std).astype(np.float32)
    Xte = ((emb[te] - mean) / std).astype(np.float32)
    lr = LogisticRegression(max_iter=3000, C=C, class_weight="balanced")
    lr.fit(Xtr, lab[tr])
    p = lr.predict(Xte)
    a = float(accuracy_score(lab[te], p))
    f = float(f1_score(lab[te], p, average="macro", zero_division=0))
    accs.append(a)
    f1s.append(f)
    print(f"  fold {k}: n={len(te):5d}  acc {a:.4f}  f1 {f:.4f}")

print()
print(f"  akurasi CV : {np.mean(accs):.4f} +/- {np.std(accs):.4f} "
      f"(min {min(accs):.4f}, maks {max(accs):.4f})")
print(f"  f1 CV      : {np.mean(f1s):.4f} +/- {np.std(f1s):.4f}")

LAPORAN.parent.mkdir(parents=True, exist_ok=True)
json.dump({
    "korpus": {"jumlah_klip": int(n), "jumlah_kelas": len(label_map)},
    "split": {"latih": int(len(idx_train)), "val": int(len(idx_val)), "uji": int(len(idx_test))},
    "uji_besar": hasil_besar,
    "cv5": {
        "akurasi_rata": float(np.mean(accs)),
        "akurasi_simpangan": float(np.std(accs)),
        "f1_rata": float(np.mean(f1s)),
        "f1_simpangan": float(np.std(f1s)),
        "per_fold": [{"akurasi": a, "f1": f} for a, f in zip(accs, f1s, strict=True)],
    },
    "pembanding": {
        "uji_127_klip": 0.7874,
        "catatan": "angka uji 127 klip dari ml/reports/metrics.json untuk membandingkan efek ukuran split",
    },
}, open(LAPORAN, "w"), indent=2)
print()
print(f"tersimpan: {LAPORAN}")
