"""Bangun gambar untuk proposal dan slide dari data nyata repo.

Semua angka berasal dari ml/reports/metrics.json, ml/data/splits.json,
ml/data/manifest.csv, dan ekspor database demo (docs/proposal/data/demo_indices.json).
Gaya: latar putih, warna datar, tanpa emoji, tanpa simbol panah.
"""
import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

ROOT = Path(__file__).resolve().parent.parent
FIG_DIR = ROOT / "docs" / "proposal" / "figures"
DATA_DIR = ROOT / "docs" / "proposal" / "data"
FIG_DIR.mkdir(parents=True, exist_ok=True)

BLUE = "#0033FF"
BLUE_SOFT = "#8AB0FF"
MINT = "#2FB79A"
SAND = "#D99A2B"
GREY = "#8F8F99"
INK = "#111114"

plt.rcParams.update({
    "figure.dpi": 200,
    "savefig.dpi": 200,
    "font.size": 9,
    "axes.edgecolor": GREY,
    "axes.labelcolor": INK,
    "text.color": INK,
    "xtick.color": INK,
    "ytick.color": INK,
    "axes.grid": True,
    "grid.color": "#E4E4E7",
    "grid.linewidth": 0.6,
    "axes.spines.top": False,
    "axes.spines.right": False,
})


def load_metrics():
    return json.loads((ROOT / "ml" / "reports" / "metrics.json").read_text())


def load_manifest():
    with open(ROOT / "ml" / "data" / "manifest.csv") as f:
        return list(csv.DictReader(f))


def load_splits():
    return json.loads((ROOT / "ml" / "data" / "splits.json").read_text())


def fig_pipeline():
    """Diagram alur sistem, kotak bernomor tanpa simbol panah."""
    fig, ax = plt.subplots(figsize=(6.6, 2.5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3.4)
    ax.axis("off")

    steps = [
        ("1", "Rekam suara\nHP atau AudioMoth"),
        ("2", "Unggah ke server\nmetadata lokasi"),
        ("3", "Antrean kerja\nRedis"),
        ("4", "Inference\nBirdNET + model lokal"),
        ("5", "Indeks soundscape\nACI, NDSI, ADI, BI"),
        ("6", "Dashboard\nverifikasi ahli"),
    ]
    x = 0.25
    width, height, gap = 1.42, 1.0, 0.26
    for number, label in steps:
        box = FancyBboxPatch(
            (x, 1.35), width, height,
            boxstyle="round,pad=0.02,rounding_size=0.08",
            linewidth=1.0, edgecolor=BLUE, facecolor="#F2F6FF",
        )
        ax.add_patch(box)
        ax.text(x + width / 2, 2.1, number, ha="center", va="center",
                fontsize=8, color=BLUE, weight="bold")
        ax.text(x + width / 2, 1.72, label, ha="center", va="center", fontsize=6.6, linespacing=1.3)
        if x > 0.3:
            ax.plot([x - gap, x], [1.85, 1.85], color=GREY, linewidth=0.9)
        x += width + gap
    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig01_alur_sistem.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def fig_per_species():
    """F1 per spesies pada data uji, diurutkan."""
    metrics = load_metrics()
    per_species = {k: v for k, v in metrics["per_species"].items() if k != "_negative"}
    items = sorted(per_species.items(), key=lambda kv: kv[1]["f1"])
    names = [k.replace(" ", "\u00a0") for k, _ in items]
    values = [v["f1"] for _, v in items]
    macro = metrics["macro_f1"]

    fig, ax = plt.subplots(figsize=(6.6, 5.4))
    colors = [MINT if v >= macro else SAND for v in values]
    ax.barh(names, values, color=colors, height=0.72)
    ax.axvline(macro, color=BLUE, linewidth=1.2, linestyle="--")
    ax.text(
        0.02, 0.98, f"Macro F1 {macro:.2f}",
        transform=ax.transAxes, va="top", ha="left", fontsize=8, color=BLUE,
        bbox=dict(facecolor="white", edgecolor=BLUE, linewidth=0.6, pad=2.5),
    )
    ax.set_xlim(0, 1.0)
    ax.set_xlabel("F1 pada data uji (25 spesies, 218 klip uji)")
    ax.grid(axis="y", visible=False)
    for i, v in enumerate(values):
        ax.text(v + 0.01, i, f"{v:.2f}", va="center", fontsize=6.4, color=INK)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig02_f1_per_spesies.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def fig_precision_recall():
    """Sebaran precision dan recall per spesies."""
    metrics = load_metrics()
    fig, ax = plt.subplots(figsize=(4.6, 4.2))
    xs, ys, labels = [], [], []
    for name, m in metrics["per_species"].items():
        if name == "_negative":
            continue
        xs.append(m["recall"])
        ys.append(m["precision"])
        labels.append(name.split()[0][0] + ". " + name.split()[1])
    ax.scatter(xs, ys, s=26, color=BLUE, alpha=0.75, edgecolor="white", linewidth=0.5)
    ax.axhline(metrics["macro_precision"], color=GREY, linewidth=0.9, linestyle=":")
    ax.axvline(metrics["macro_recall"], color=GREY, linewidth=0.9, linestyle=":")
    ax.set_xlim(0, 1.02)
    ax.set_ylim(0, 1.02)
    ax.set_xlabel("Recall")
    ax.set_ylabel("Precision")
    for x, y, label in zip(xs, ys, labels, strict=True):
        if y > 0.9 or x < 0.3:
            ax.annotate(label, (x, y), textcoords="offset points", xytext=(4, 2), fontsize=5.8, color=GREY)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig03_precision_recall.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def fig_dataset():
    """Komposisi dataset latih: jumlah klip per split dan jumlah spesies."""
    splits = load_splits()
    manifest = load_manifest()
    species = sorted({r["species_scientific"] for r in manifest})
    counts = {k: len(v) for k, v in splits.items() if isinstance(v, list)}

    fig, axes = plt.subplots(1, 2, figsize=(6.6, 2.6))
    labels = ["Train", "Validasi", "Uji"]
    values = [counts.get("train", 0), counts.get("val", 0), counts.get("test", 0)]
    axes[0].bar(labels, values, color=[BLUE, BLUE_SOFT, MINT], width=0.55)
    for i, v in enumerate(values):
        axes[0].text(i, v + 12, str(v), ha="center", fontsize=8)
    axes[0].set_ylabel("Jumlah klip")
    axes[0].set_title("Pembagian data per split", fontsize=9)
    axes[0].set_ylim(0, max(values) * 1.2)
    axes[0].grid(axis="x", visible=False)

    ok = len(species)
    axes[1].bar(["Spesies target", "Kelas negatif"], [ok, 1], color=[BLUE, SAND], width=0.5)
    for i, v in enumerate([ok, 1]):
        axes[1].text(i, v + 0.6, str(v), ha="center", fontsize=8)
    axes[1].set_title("Cakupan kelas model lokal", fontsize=9)
    axes[1].set_ylim(0, ok * 1.3)
    axes[1].grid(axis="x", visible=False)

    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig04_dataset.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def fig_indices():
    """Indeks soundscape rekaman demo, hasil hitung worker."""
    path = DATA_DIR / "demo_indices.json"
    if not path.exists():
        print("lewati fig05: docs/proposal/data/demo_indices.json belum ada")
        return
    rows = [
        r for r in json.loads(path.read_text())
        if (r.get("duration_s") or 0) >= 10  # klip di bawah 10 detik terlalu pendek untuk indeks
    ]
    metrics = [
        ("aci", "ACI (Acoustic Complexity Index)", 1.0),
        ("ndsi", "NDSI (rasio biophony dan anthrophony)", 1.0),
        ("adi", "ADI (Acoustic Diversity Index)", 2.0),
        ("bi", "BI (Bioacoustics Index)", 1.0),
    ]
    fig, axes = plt.subplots(1, 4, figsize=(6.6, 2.2))
    for ax, (key, title, _) in zip(axes, metrics, strict=True):
        values = [r.get(key) if r.get(key) is not None else 0 for r in rows]
        ax.bar(range(len(values)), values, color=BLUE, width=0.62)
        ax.set_title(title, fontsize=6.6, linespacing=1.2)
        ax.set_xticks(range(len(values)))
        ax.set_xticklabels([str(r["recording_id"]) for r in rows], fontsize=6)
        ax.tick_params(axis="y", labelsize=6)
        ax.grid(axis="x", visible=False)
    axes[1].set_ylim(0, 1.0)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig05_indeks_soundscape.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def fig_thresholds():
    """Sebaran threshold terkalibrasi per spesies."""
    metrics = load_metrics()
    thresholds = metrics["thresholds"]
    values = sorted(v for k, v in thresholds.items() if k != "_negative")
    fig, ax = plt.subplots(figsize=(4.6, 2.6))
    ax.hist(values, bins=8, color=BLUE_SOFT, edgecolor=BLUE, linewidth=0.7)
    ax.set_xlabel("Threshold terkalibrasi")
    ax.set_ylabel("Jumlah spesies")
    ax.grid(axis="x", visible=False)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig06_threshold.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def fig_peta_lokasi():
    """Sebaran lokasi monitoring dari koordinat nyata.

    Titik diberi nomor dan daftar nama ditaruh di legenda, supaya label tidak
    saling menumpuk ketika beberapa lokasi berdekatan (kasus Jawa Barat).
    """
    import json as _json
    path = DATA_DIR / "demo_sites.json"
    if not path.exists():
        print("lewati fig07: demo_sites.json belum ada")
        return
    rows = sorted(_json.loads(path.read_text()), key=lambda r: r["longitude"])
    fig, ax = plt.subplots(figsize=(6.6, 3.6))
    from matplotlib.lines import Line2D

    handles = []
    xs, ys = [], []
    for index, row in enumerate(rows, start=1):
        xs.append(row["longitude"])
        ys.append(row["latitude"])
        ax.scatter([row["longitude"]], [row["latitude"]], s=52, color=BLUE, zorder=3)
        ax.annotate(
            str(index), (row["longitude"], row["latitude"]),
            textcoords="offset points", xytext=(0, -3), ha="center",
            fontsize=6.2, color="white", weight="bold", zorder=4,
        )
        handles.append(Line2D([], [], marker="o", linestyle="none", color=BLUE,
                              markersize=5, label=f"{index}. {row['name']} "
                                                   f"({row['latitude']:.2f}, {row['longitude']:.2f})"))

    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_xlim(min(xs) - 3, max(xs) + 3)
    ax.set_ylim(min(ys) - 1.0, max(ys) + 1.0)
    ax.legend(handles=handles, loc="center left", bbox_to_anchor=(1.02, 0.5),
              fontsize=6.2, frameon=False, labelspacing=0.7)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig07_peta_lokasi.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    fig_pipeline()
    fig_per_species()
    fig_precision_recall()
    fig_dataset()
    fig_indices()
    fig_thresholds()
    fig_peta_lokasi()
    for f in sorted(FIG_DIR.glob("*.png")):
        print(f"{f.name} {f.stat().st_size // 1024} KB")
