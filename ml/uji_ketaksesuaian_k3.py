"""Ukur ketaksesuaian latih/saji pada K3 (jendela bersuara).

Kecurigaan yang diuji: CV K3 memberi F1 0,8051 (lulus C14), tetapi angka itu
diukur pada embedding RATA-RATA per klip, sedangkan jalur produksi
`ml/engines/embedding_clf.py` mengklasifikasi PER JENDELA dan tidak pernah
merata-ratakan apa pun (`grep -c "mean(axis=0)" ml/engines/embedding_clf.py`
= 0). Vektor rata-rata tidak pernah muncul saat menyaji.

Kalau model yang dilatih pada rata-rata ternyata jauh lebih buruk ketika diberi
jendela tunggal, maka angka 0,8051 mengukur tugas yang berbeda dari yang
dikerjakan produksi, dan tidak boleh dipakai sebagai bukti C14.

Latih sekali pada klip latih (rata-rata), lalu uji pada klip UJI yang sama
dengan dua cara:
  A. rata-rata jendela per klip  (seperti CV K3)
  B. jendela tunggal, lalu satu klip diputuskan dari jendela terbaiknya
     (seperti produksi: tiap jendela dinilai sendiri)

Jalankan: source .venv/bin/activate && python ml/uji_ketaksesuaian_k3.py
"""
from __future__ import annotations

import collections
import json
import re
import sys
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression

ROOT = Path(__file__).resolve().parent.parent
ML = ROOT / "ml"
POLA = re.compile(r"__w\d+$")


def main() -> int:
    klip_dir = ML / "embeddings_bersuara_v3_klip"
    jnd_dir = ML / "embeddings_bersuara_v3"
    sp = json.loads((ML / "data" / "splits_v3_nd_bersih.json").read_text())

    ids_k = json.loads((klip_dir / "clip_ids.json").read_text())
    X_k = np.load(klip_dir / "embeddings.npy")
    y_k = np.load(klip_dir / "labels.npy")
    lm = json.loads((klip_dir / "label_map.json").read_text())
    idx_k = {c: i for i, c in enumerate(ids_k)}

    latih = [c for c in (list(sp["train"]) + list(sp["val"])) if c in idx_k]
    uji = [c for c in sp["test"] if c in idx_k]
    print(f"klip latih {len(latih)}, klip uji {len(uji)}, kelas {len(lm)}")

    Xtr = X_k[[idx_k[c] for c in latih]]
    ytr = y_k[[idx_k[c] for c in latih]]
    mean, std = Xtr.mean(axis=0), Xtr.std(axis=0) + 1e-6
    Xtr_n = (Xtr - mean) / std

    print("melatih LogReg pada embedding RATA-RATA klip...")
    clf = LogisticRegression(max_iter=3000, C=1.0, class_weight="balanced")
    clf.fit(Xtr_n, ytr)

    # Cara A: rata-rata per klip, sama seperti CV K3.
    Xte = (X_k[[idx_k[c] for c in uji]] - mean) / std
    yte = y_k[[idx_k[c] for c in uji]]
    akur_a = float((clf.predict(Xte) == yte).mean())

    # Cara B: jendela tunggal, seperti yang benar-benar dilihat produksi.
    ids_j = json.loads((jnd_dir / "clip_ids.json").read_text())
    X_j = np.load(jnd_dir / "embeddings.npy", mmap_mode="r")
    per_klip: dict[str, list[int]] = collections.defaultdict(list)
    for i, cid in enumerate(ids_j):
        per_klip[POLA.sub("", cid)].append(i)

    benar_b = benar_mayoritas = 0
    n_jendela_benar = n_jendela_total = 0
    for c, yb in zip(uji, yte, strict=True):
        rows = per_klip.get(c, [])
        if not rows:
            continue
        blok = (np.asarray(X_j[rows], dtype=np.float32) - mean) / std
        pred = clf.predict(blok)
        prob = clf.predict_proba(blok)
        n_jendela_total += len(rows)
        n_jendela_benar += int((pred == yb).sum())
        # Produksi menerima deteksi dari jendela mana pun yang melewati ambang,
        # jadi "klip benar" kalau ada jendela yang menebak benar dengan
        # keyakinan tertinggi.
        kelas_terbaik = int(pred[int(np.argmax(prob.max(axis=1)))])
        if kelas_terbaik == yb:
            benar_b += 1
        if collections.Counter(pred.tolist()).most_common(1)[0][0] == yb:
            benar_mayoritas += 1

    n = len(uji)
    print()
    print("Model SAMA, klip uji sama, dua cara memberi masukan:")
    print(f"  A. rata-rata jendela (seperti CV K3)      : {akur_a:.4f}")
    print(f"  B. jendela terkuat   (seperti produksi)   : {benar_b / n:.4f}")
    print(f"  B'. suara terbanyak antar jendela         : {benar_mayoritas / n:.4f}")
    print(f"  akurasi tiap jendela sendiri              : {n_jendela_benar / n_jendela_total:.4f}"
          f"  (n={n_jendela_total} jendela)")
    selisih = akur_a - benar_b / n
    print()
    print(f"selisih A dikurangi B = {selisih:+.4f}")
    if selisih > 0.05:
        print("KESIMPULAN: ketaksesuaian MATERIAL. Angka CV K3 mengukur tugas yang")
        print("berbeda dari yang dikerjakan produksi, jadi tidak sah dipakai C14")
        print("sebelum engine ikut merata-ratakan jendela.")
    else:
        print("KESIMPULAN: ketaksesuaian kecil pada pool ini.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
