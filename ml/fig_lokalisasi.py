"""Gambar ilustrasi cara aplikasi menampilkan asal suara.

Panel kiri: perangkat satu kanal, yang bisa ditampilkan hanya perkiraan
jangkauan deteksi berupa lingkaran, bukan posisi sumber.
Panel kanal kanan: perangkat banyak kanal, yang bisa menampilkan arah datang
beserta rentang jarak dan sektornya.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from matplotlib.axes import Axes
from matplotlib.patches import Circle, Wedge

KELUARAN = Path(__file__).resolve().parent.parent / "docs" / "proposal" / "figures" / "fig09_lokalisasi.png"
WARNA_UTAMA = "#4C7DFF"
WARNA_KEDUA = "#6F9B68"
WARNA_LEMBUT = "#B9C4D8"


def panel_satu_mikrofon(ax: Axes) -> None:
    """Lingkaran jangkauan per spesies pada perangkat satu kanal."""
    ax.set_title("Satu mikrofon: perkiraan jangkauan deteksi", fontsize=11)
    for radius, nama, warna_garis, warna_teks in (
        (30.0, "spesies bersuara pelan, jangkauan sekitar 30 m", WARNA_LEMBUT, "#4A5568"),
        (60.0, "spesies bersuara sedang, jangkauan sekitar 60 m", WARNA_UTAMA, "#2F5BD0"),
        (100.0, "spesies bersuara keras, jangkauan sekitar 100 m", WARNA_KEDUA, "#3F6B3A"),
    ):
        ax.add_patch(Circle((0, 0), radius, fill=False, edgecolor=warna_garis, linewidth=1.6))
        ax.text(
            radius * 0.66,
            radius * 0.70,
            nama,
            fontsize=7.5,
            color=warna_teks,
            bbox=dict(facecolor="white", edgecolor="none", pad=1.4),
        )
    ax.plot([0], [0], marker="^", markersize=9, color="#111111")
    ax.text(2, -8, "alat perekam", fontsize=8)
    ax.text(
        0,
        -118,
        "Yang bisa ditampilkan hanya jarak jangkauan.\n"
        "Posisi sumber tidak bisa diketahui dari satu kanal.",
        fontsize=8,
        ha="center",
        color="#333333",
    )
    ax.set_xlim(-138, 138)
    ax.set_ylim(-132, 128)
    ax.set_aspect("equal")
    ax.grid(alpha=0.18, linewidth=0.6)


def panel_banyak_kanal(ax: Axes) -> None:
    """Arah datang, rentang jarak, dan titik perkiraan sumber."""
    ax.set_title("Tiga kanal atau lebih: arah datang dan rentang jarak", fontsize=11)
    azimuth = 137.0
    theta = np.radians(azimuth)
    jarak_dekat, jarak_jauh = 20.0, 36.0

    ax.add_patch(Wedge((0, 0), jarak_jauh, azimuth - 8, azimuth + 8, facecolor=WARNA_UTAMA, alpha=0.18, edgecolor="none"))
    ax.plot([0, jarak_jauh * np.cos(theta)], [0, jarak_jauh * np.sin(theta)], color=WARNA_UTAMA, linewidth=1.4)
    for radius in (jarak_dekat, jarak_jauh):
        ax.add_patch(
            Wedge((0, 0), radius, azimuth - 8, azimuth + 8, fill=False, edgecolor=WARNA_UTAMA, linewidth=0.8, linestyle=(0, (3, 3)))
        )
    ax.plot([jarak_dekat * np.cos(theta)], [jarak_dekat * np.sin(theta)], marker="o", markersize=6, color="#C0392B")
    ax.text(jarak_dekat * np.cos(theta) + 3, jarak_dekat * np.sin(theta) + 2, "perkiraan sumber", fontsize=8, color="#C0392B")
    ax.plot([0], [0], marker="^", markersize=9, color="#111111")
    ax.text(2, -8, "array 4 mikrofon, bentang 0,5 m", fontsize=8)
    ax.text(
        12,
        62,
        "Arah 137 derajat, \nsimpangan 8 derajat,\njarak 20 sampai 36 m",
        fontsize=8,
        color=WARNA_UTAMA,
    )
    ax.text(
        0,
        -118,
        "Sudut diukur dari selisih waktu tiba antar kanal.\n"
        "Rentang jarak dari penyusutan amplitudo setelah kalibrasi.",
        fontsize=8,
        ha="center",
        color="#333333",
    )
    ax.set_xlim(-138, 138)
    ax.set_ylim(-132, 128)
    ax.set_aspect("equal")
    ax.grid(alpha=0.18, linewidth=0.6)


def main() -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    gambar, (kiri, kanan) = plt.subplots(1, 2, figsize=(11, 5.4), dpi=200)
    panel_satu_mikrofon(kiri)
    panel_banyak_kanal(kanan)
    for ax in (kiri, kanan):
        ax.set_xlabel("meter")
        ax.set_ylabel("meter")
    gambar.suptitle("Cara aplikasi menampilkan asal suara menurut jumlah kanal mikrofon", fontsize=12)
    gambar.tight_layout(rect=(0, 0, 1, 0.96))
    KELUARAN.parent.mkdir(parents=True, exist_ok=True)
    gambar.savefig(KELUARAN)
    print("gambar disimpan:", KELUARAN)


if __name__ == "__main__":
    main()
