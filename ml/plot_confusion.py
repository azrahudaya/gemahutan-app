"""Confusion matrix 26x26 untuk data uji, plus ROC OvR per spesies.

Load embedding BirdNET, jalankan MLP untuk semua 127 jendela uji, hitung
confusion matrix, render heatmap 26x26 (label nama species English/Indonesia),
dan render grid 6x5 ROC OvR untuk 26 kelas (25 spesies + 1 negatif).

Hasil:
  docs/proposal/figures/fig10_confusion_matrix.png
  docs/proposal/figures/fig13_roc_per_species.png
  ml/reports/confusion_top.md
  ml/reports/roc_per_species.md

Juga mengaudit kelas dengan AUC < 0.5 (kurang dari tebakan acak) untuk
ditandai perlu perbaikan.
"""
import json
import sys
from pathlib import Path

import numpy as np

ML_DIR = Path(__file__).resolve().parent
REPO_DIR = ML_DIR.parent
sys.path.insert(0, str(REPO_DIR))
sys.path.insert(0, str(ML_DIR))

from ml.train import MLP  # noqa: E402

EMB_DIR = ML_DIR / "embeddings"
CKPT = ML_DIR / "checkpoints" / "best_model.npz"
NORM = ML_DIR / "checkpoints" / "normalization.npz"
SPLITS = ML_DIR / "data" / "splits.json"
REPORTS = ML_DIR / "reports"
FIG = REPO_DIR / "docs" / "proposal" / "figures"

# Pemetaan kode -> nama English (nama ilmiah) -> nama Indonesia untuk label.
# Diambil dari ml/data/species_list.json dan docs/proposal/USB2026_Proposal.md.
NAMA_INDONESIA = {
    "Aegithina tiphia": "Cipoh kacat",
    "Amaurornis phoenicurus": "Kareo padi",
    "Anthreptes malacensis": "Burung madu sriganti",
    "Aplonis panayensis": "Perling kacamata",
    "Arachnothera longirostra": "Pijantung kecil",
    "Centropus bengalensis": "Bubut alang-alang",
    "Chalcophaps indica": "Delimut zamrud",
    "Cinnyris jugularis": "Burung madu sriganti",
    "Cisticola juncidis": "Cici merah",
    "Corvus macrorhynchos": "Gagak kampung",
    "Dicrurus macrocercus": "Srigunting hitam",
    "Gallus gallus": "Ayam kampung",
    "Geopelia striata": "Merpatu striata",
    "Haliastur indus": "Elang bondol",
    "Hirundo tahitica": "Layang-layang",
    "Lonchura punctulata": "Bondol peking",
    "Merops philippinus": "Kirik-kirik biru",
    "Orthotomus sutorius": "Cinenen pisang",
    "Passer montanus": "Burung gereja",
    "Prinia familiaris": "Perenjak jawa",
    "Pycnonotus aurigaster": "Kutilang",
    "Pycnonotus goiavier": "Merbah cerukcuk",
    "Rhipidura javanica": "Kipasan belang",
    "Spilopelia chinensis": "Tekukur biasa",
    "Todiramphus chloris": "Cekakak sungai",
    "_negative": "Latar (non-target)",
}


def muat(label_map):
    emb = np.load(EMB_DIR / "embeddings.npy")
    labels = np.load(EMB_DIR / "labels.npy")
    with open(EMB_DIR / "clip_ids.json") as f:
        ids = json.load(f)
    with open(SPLITS) as f:
        sp = json.load(f)
    cid_idx = {c: i for i, c in enumerate(ids)}
    idx = [cid_idx[c] for c in sp["test"] if c in cid_idx]
    inv = {v: k for k, v in label_map.items()}
    return emb[idx], labels[idx], inv


def label_label(inv_map, nama_indonesia):
    """Label untuk heatmap: nama Inggris (Indonesia) singkat."""
    out = []
    for i in range(len(inv_map)):
        nama = inv_map[i]
        idn = nama_indonesia.get(nama, "")
        if nama == "_negative":
            out.append("_negative")
        else:
            # Singkat nama Indonesia supaya tidak menabrak cell.
            singkatan = idn.split()[0] if idn else nama.split()[0]
            out.append(f"{singkatan}\n({nama.split()[0][:5]}.)")
    return out


def hitung_dan_render_cm():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import seaborn as sns

    with open(EMB_DIR / "label_map.json") as f:
        label_map = json.load(f)
    norm = np.load(NORM)
    mean, std = norm["mean"], norm["std"]
    X, y, inv = muat(label_map)
    n = len(label_map)
    model = MLP(1024, 256, n)
    model.load(str(CKPT))
    raw_probs = model.forward((X - mean) / std)
    ckpt = np.load(CKPT, allow_pickle=False)
    has_calibration = "temperature" in ckpt.files and "bias" in ckpt.files
    if has_calibration:
        T = float(ckpt["temperature"].reshape(-1)[0])
        bias = ckpt["bias"].astype(np.float32)
        # logits = log(raw_probs) disusun ulang agar pasca-kalibrasi = softmax((logits+bias)/T).
        eps = 1e-9
        raw_clipped = np.clip(raw_probs, eps, 1.0)
        logits = np.log(raw_clipped)
        scaled = (logits + bias) / T
        scaled -= scaled.max(axis=1, keepdims=True)
        exp = np.exp(scaled)
        probs = exp / exp.sum(axis=1, keepdims=True)
    else:
        probs = raw_probs
    preds = np.argmax(probs, axis=1)

    cm = np.zeros((n, n), dtype=np.int32)
    for t, p in zip(y, preds, strict=True):
        cm[t, p] += 1
    # Normalized per-row (recall) untuk ranking confusion.
    row_sum = cm.sum(axis=1, keepdims=True)
    cm_norm = np.where(row_sum > 0, cm / row_sum, 0)

    # Label dengan nama English/Indonesia.
    labels = label_label(inv, NAMA_INDONESIA)

    fig, ax = plt.subplots(figsize=(12, 10), dpi=150)
    sns.heatmap(
        cm_norm,
        annot=True,
        fmt=".2f",
        cmap="YlOrRd",
        xticklabels=labels,
        yticklabels=labels,
        cbar_kws={"label": "Proporsi benar-benar kelas ini"},
        ax=ax,
        vmin=0,
        vmax=1,
    )
    ax.set_xlabel("Prediksi model")
    ax.set_ylabel("Label benar")
    ax.set_title(
        f"Confusion Matrix 26x26 -- Uji Bersih (n={len(y)} jendela, ND-free)\n"
        "Diagonal = recall per kelas. Warna lebih gelap = recall lebih tinggi."
    )
    plt.xticks(rotation=60, ha="right", fontsize=7)
    plt.yticks(rotation=0, fontsize=7)
    plt.tight_layout()
    out = FIG / "fig10_confusion_matrix.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  tulis {out} ({out.stat().st_size} B)")

    # 10 confusion teratas (di luar diagonal).
    pairs = []
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            if cm_norm[i, j] > 0:
                pairs.append((cm_norm[i, j], cm[i, j], inv[i], inv[j]))
    pairs.sort(reverse=True)
    top = pairs[:10]

    md = ["# Confusion Teratas (Uji Bersih, Normalized per Baris)", ""]
    md.append("Sepuluh pasangan kelas yang paling sering keliru diprediksi, ")
    md.append("diurutkan dari nilai normalized-row terbesar. ")
    md.append("`cm_norm` adalah proporsi jendela kelas-benarnya yang diprediksi ")
    md.append("sebagai kelas-target. `count` adalah jumlah jendela.")
    md.append("")
    md.append("| # | cm_norm | count | Label benar | Diprediksi sebagai |")
    md.append("|---|---------|-------|-------------|---------------------|")
    for i, (nm, cnt, benar, tebakan) in enumerate(top, 1):
        md.append(f"| {i} | {nm:.3f} | {cnt} | {benar} | {tebakan} |")
    md.append("")
    md.append(f"Total jendela uji: {len(y)}. Akurasi top-1: {np.mean(preds == y):.4f}.")
    (REPORTS / "confusion_top.md").write_text("\n".join(md))
    print(f"  tulis {REPORTS / 'confusion_top.md'}")

    return probs, y, inv, label_map


def render_roc(probs, y, inv, label_map):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from sklearn.metrics import auc, roc_curve

    n = len(label_map)
    # 6 baris x 5 kolom untuk 26 cell (termasuk _negative), pakai sel kosong
    # di akhir jika 26 tidak habis 30.
    fig, axes = plt.subplots(6, 5, figsize=(20, 22), dpi=120)
    axes = axes.flatten()

    audit = []
    for idx in range(n):
        ax = axes[idx]
        nama = inv[idx]
        # Label biner OvR: apakah kelas ini atau bukan.
        y_true = (y == idx).astype(int)
        y_score = probs[:, idx]
        if y_true.sum() == 0 or y_true.sum() == len(y_true):
            # Degenerate, tampilkan placeholder.
            ax.set_title(f"{nama}\n(tidak ada support)", fontsize=9)
            ax.axis("off")
            continue
        fpr, tpr, _ = roc_curve(y_true, y_score)
        roc_auc = auc(fpr, tpr)
        ax.plot(fpr, tpr, color="#1f77b4", lw=1.5, label=f"AUC={roc_auc:.3f}")
        ax.plot([0, 1], [0, 1], color="gray", lw=0.7, ls="--")
        support = int(y_true.sum())
        idn = NAMA_INDONESIA.get(nama, "")
        ax.set_title(f"{nama}\n{idn} (n={support})", fontsize=8)
        ax.set_xlabel("FPR", fontsize=7)
        ax.set_ylabel("TPR", fontsize=7)
        ax.tick_params(labelsize=6)
        ax.legend(loc="lower right", fontsize=6)
        audit.append((nama, support, float(roc_auc)))

    # Sel tambahan.
    for j in range(n, len(axes)):
        axes[j].axis("off")

    fig.suptitle(
        "ROC OvR per Spesies -- Uji Bersih (n=127 jendela)\n"
        "AUC < 0.5 = lebih buruk dari acak; tandai untuk perbaikan",
        fontsize=13,
    )
    plt.tight_layout(rect=[0, 0, 1, 0.97])
    out = FIG / "fig13_roc_per_species.png"
    fig.savefig(out, dpi=120, bbox_inches="tight")
    plt.close(fig)
    print(f"  tulis {out} ({out.stat().st_size} B)")

    # Audit AUC.
    audit.sort(key=lambda x: x[2])
    md = ["# Audit ROC per Spesies (OvR, Uji Bersih)", ""]
    md.append("| Species | Support | AUC | Status |")
    md.append("|---|---|---|---|")
    for nama, support, roc_auc in audit:
        if roc_auc < 0.5:
            status = "PERLU PERBAIKAN (AUC < 0.5)"
        elif roc_auc < 0.7:
            status = "rendah"
        elif roc_auc < 0.85:
            status = "cukup"
        else:
            status = "baik"
        md.append(f"| {nama} | {support} | {roc_auc:.3f} | {status} |")
    (REPORTS / "roc_per_species.md").write_text("\n".join(md))
    print(f"  tulis {REPORTS / 'roc_per_species.md'}")

    buruk = [a for a in audit if a[2] < 0.5]
    print(f"  AUC < 0.5: {len(buruk)} kelas -> {[b[0] for b in buruk]}")
    return audit


if __name__ == "__main__":
    FIG.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    print("[1/2] Confusion matrix + top-10 ...")
    probs, y, inv, label_map = hitung_dan_render_cm()
    print("[2/2] ROC OvR per spesies ...")
    render_roc(probs, y, inv, label_map)
    print("Selesai.")