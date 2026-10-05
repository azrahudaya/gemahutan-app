"""Grafik F1 per spesies dari prediksi out-of-fold CV bersarang (model produksi LR v3).

Jalankan dari akar repo: python3 docs/assets/diagram_src/buat_grafik_f1.py
Sumber angka: ml/reports/oof_bersarang.npz (dibuat ml/evaluasi_bersarang.py).
"""
import json
from pathlib import Path

import matplotlib
import matplotlib.ticker
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "docs/assets/diagrams"
for f in font_manager.findSystemFonts():
    if "PlusJakartaSans" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams["font.family"] = "Plus Jakarta Sans"

d = np.load(ROOT / "ml/reports/oof_bersarang.npz", allow_pickle=False)
P, y = d["probs"], d["y"]
lm = json.loads((ROOT / "ml/embeddings_v3/label_map.json").read_text())
inv = {v: k for k, v in lm.items()}
pred = P.argmax(1)
baris = []
for k in sorted(set(y.tolist())):
    tp = int(np.sum((pred == k) & (y == k)))
    fp = int(np.sum((pred == k) & (y != k)))
    fn = int(np.sum((pred != k) & (y == k)))
    f1 = 2 * tp / (2 * tp + fp + fn) if (2 * tp + fp + fn) else 0.0
    baris.append((inv[k], f1, int(np.sum(y == k))))
kelas = [b for b in baris if b[0] != "_negative"]
f1_makro = float(np.mean([b[1] for b in baris]))  # atas semua kelas yang muncul, termasuk _negative
kelas.sort(key=lambda b: b[1])

fig, ax = plt.subplots(figsize=(6.3, 4.6), dpi=300)
warna = ["#A7D7B8" if f < 0.55 else "#00873F" for _, f, _ in kelas]
ax.barh(range(len(kelas)), [f for _, f, _ in kelas], color=warna, height=0.72)
ax.set_yticks(range(len(kelas)))
ax.set_yticklabels([f"{n} (n={c})" for n, _, c in kelas], fontsize=6.3, style="italic")
for i, (_, f, _) in enumerate(kelas):
    ax.text(f + 0.008, i, f"{f:.2f}".replace(".", ","), va="center", fontsize=5.8, color="#27272A")
ax.axvline(f1_makro, color="#52525B", linestyle="--", linewidth=0.8)
ax.text(f1_makro + 0.01, len(kelas) - 0.15, f"F1 makro {f1_makro:.3f}".replace(".", ","), fontsize=6.5, color="#52525B")
ax.set_xlim(0, 1.05)
ax.set_ylim(-0.7, len(kelas) + 0.6)
ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:.1f}".replace(".", ",")))
ax.set_xlabel("F1 per spesies (out-of-fold, 5 lipatan per perekam)", fontsize=7)
ax.tick_params(axis="x", labelsize=6.5)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
ax.spines["left"].set_color("#A1A1AA")
ax.spines["bottom"].set_color("#A1A1AA")
fig.tight_layout()
OUT.mkdir(parents=True, exist_ok=True)
fig.savefig(OUT / "f1_per_spesies.png", dpi=300)
(OUT / "f1_per_spesies.json").write_text(json.dumps(
    {"f1_makro_semua_kelas": round(f1_makro, 4), "per_spesies": {n: round(f, 4) for n, f, _ in kelas}}, indent=2))
print("F1 makro", round(f1_makro, 4), "| terlemah:", [(n, round(f, 2)) for n, f, _ in kelas[:5]])
