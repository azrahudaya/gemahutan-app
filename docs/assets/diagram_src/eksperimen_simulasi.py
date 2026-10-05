"""Eksperimen simulasi perkiraan lokasi untuk proposal (Bagian 7.3).

Tiga alat virtual, masing-masing larik 4 mikrofon bujur sangkar 0,5 m, dipasang
membentuk segitiga. Sumber suara buatan ditaruh acak di dalam area pantau, lalu
arah dari tiap alat dihitung dengan GCC-PHAT (ml/localization.estimasi_arah) dan
digabung dengan triangulasi. Sinyal buatan tanpa gema: ini batas atas mutu,
bukan angka lapangan.

    .venv/bin/python docs/assets/diagram_src/eksperimen_simulasi.py
Keluaran: docs/assets/data/simulasi_lokasi.json, docs/assets/diagrams/simulasi_lokasi.png
"""
import json
import sys
from pathlib import Path

import numpy as np

AKAR = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(AKAR))

from ml.localization import bangun_sintetis, estimasi_arah, triangulasi  # noqa: E402

SR = 16000
LARIK = [(-0.25, -0.25), (0.25, -0.25), (0.25, 0.25), (-0.25, 0.25)]
ALAT = [(-60.0, -40.0), (60.0, -40.0), (0.0, 64.0)]
SNR = (20, 10, 5, 0)
N_SUMBER = 30


def arah_dan_jarak(dari, ke):
    dx, dy = ke[0] - dari[0], ke[1] - dari[1]
    return float(np.degrees(np.arctan2(dy, dx)) % 360), float(np.hypot(dx, dy))


def satu_percobaan(sumber, snr, benih):
    arah = []
    for i, alat in enumerate(ALAT):
        az, jarak = arah_dan_jarak(alat, sumber)
        kanal = bangun_sintetis(az, jarak, LARIK, sr=SR, snr_db=snr, benih=benih * 10 + i)
        h = estimasi_arah(kanal, SR, LARIK)
        if h is None:
            return None
        arah.append((alat[0], alat[1], h.azimuth_deg))
    pos = triangulasi(arah, kotak_m=120.0, langkah_m=1.0)
    return float(np.hypot(pos.x_m - sumber[0], pos.y_m - sumber[1])), arah, pos


def main():
    rng = np.random.default_rng(2026)
    sumber = [(float(rng.uniform(-50, 50)), float(rng.uniform(-35, 50))) for _ in range(N_SUMBER)]
    hasil = {}
    contoh = None
    for snr in SNR:
        galat = []
        for k, s in enumerate(sumber):
            r = satu_percobaan(s, snr, k)
            if r is None:
                continue
            galat.append(r[0])
            if snr == 10 and k == 3:
                contoh = {"sumber": s, "arah": r[1], "perkiraan": (r[2].x_m, r[2].y_m), "galat_m": r[0]}
        g = np.array(galat)
        hasil[str(snr)] = {"n": int(g.size), "median_m": round(float(np.median(g)), 2),
                           "p90_m": round(float(np.percentile(g, 90)), 2), "maks_m": round(float(g.max()), 2)}
        print(snr, hasil[str(snr)])
    keluar = {"alat": ALAT, "larik_m": LARIK, "sr": SR, "n_sumber": N_SUMBER, "per_snr": hasil, "contoh": contoh,
              "catatan": "sinyal buatan tanpa gema, jam alat dianggap sinkron"}
    (AKAR / "docs/assets/data/simulasi_lokasi.json").write_text(json.dumps(keluar, indent=1))
    gambar(keluar)


def gambar(d):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    hijau, hijau_tua, abu = "#00873F", "#00602D", "#71717A"
    plt.rcParams["font.family"] = "Times New Roman"
    fig, (a, b) = plt.subplots(1, 2, figsize=(9.2, 3.9), gridspec_kw={"width_ratios": [1.05, 1]})
    c = d["contoh"]
    for (x, y, az) in c["arah"]:
        t = np.radians(az)
        a.plot([x, x + 160 * np.cos(t)], [y, y + 160 * np.sin(t)], color=hijau, lw=1, alpha=.7)
    ax, ay = zip(*d["alat"], strict=True)
    a.scatter(ax, ay, marker="s", s=60, color=hijau_tua, zorder=3, label="alat virtual")
    a.scatter(*c["sumber"], marker="*", s=180, color="#B45309", zorder=4, label="sumber sebenarnya")
    a.add_patch(plt.Circle(c["perkiraan"], max(c["galat_m"], 3) * 2, color=hijau, alpha=.18, zorder=2,
                           label="area perkiraan"))
    a.scatter(*c["perkiraan"], marker="x", s=50, color="black", zorder=5, label="titik perkiraan")
    a.set_xlim(-90, 90)
    a.set_ylim(-70, 95)
    a.set_aspect("equal")
    a.set_xlabel("meter")
    a.set_ylabel("meter")
    a.set_title("(a) Contoh: 3 alat, SNR 10 dB", fontsize=11)
    a.legend(fontsize=8, loc="upper right", frameon=False)
    a.grid(alpha=.25)

    snr = list(d["per_snr"].keys())
    med = [d["per_snr"][s]["median_m"] for s in snr]
    p90 = [d["per_snr"][s]["p90_m"] for s in snr]
    xs = np.arange(len(snr))
    b.bar(xs - .18, med, .36, color=hijau, label="median")
    b.bar(xs + .18, p90, .36, color="#A7D7B8", label="persentil 90")
    for i, (m, p) in enumerate(zip(med, p90, strict=True)):
        b.text(i - .18, m, f"{m:.1f}".replace(".", ","), ha="center", va="bottom", fontsize=8)
        b.text(i + .18, p, f"{p:.1f}".replace(".", ","), ha="center", va="bottom", fontsize=8)
    b.set_xticks(xs, [f"{s} dB" for s in snr])
    b.set_xlabel("SNR sinyal")
    b.set_ylabel("galat posisi (meter)")
    b.set_title(f"(b) Galat posisi, {d['n_sumber']} sumber acak", fontsize=11)
    b.legend(fontsize=8, frameon=False)
    b.grid(axis="y", alpha=.25)
    from matplotlib.ticker import FuncFormatter
    b.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.1f}".replace(".", ",")))
    for s in ("top", "right"):
        a.spines[s].set_visible(False)
        b.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig(AKAR / "docs/assets/diagrams/simulasi_lokasi.png", dpi=220)


if __name__ == "__main__":
    main()
