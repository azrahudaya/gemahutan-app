"""Kumpulkan angka proposal dari berkas sumber, bukan diketik ulang.

Sumber:
  ml/data/species_list.json                      daftar 25 spesies + nama Indonesia
  ml/reports/eval_bersarang.json                 CV bersarang per perekam
  ml/reports/uji_independen.json                 uji independen (tanpa label)
  docs/assets/data/e2e_produksi_385147c.json     uji end-to-end jalur produksi
  docs/assets/diagrams/f1_per_spesies.json       F1 per spesies (OOF)
  git                                            tanggal mulai dan jumlah commit
  ml/reports/latensi.json                        waktu proses rekaman 60 menit
  docs/assets/data/simulasi_lokasi.json          eksperimen simulasi perkiraan lokasi
Jumlah test dihitung manual pada 3 Okt 2026 (lihat KONSTAN).
"""
import json
import subprocess
from pathlib import Path

AKAR = Path(__file__).resolve().parents[3]

KONSTAN = {
    # jumlah kasus test otomatis per 5 Okt 2026 (API dihitung dengan pytest --collect-only)
    "test": {"API": 139, "worker": 33, "ML": 28, "web": 57},
}


def koma(x, d=3):
    return f"{x:.{d}f}".replace(".", ",")


def _json(rel):
    return json.loads((AKAR / rel).read_text())


def _metrik(rows):
    tp = sum(len(set(r["terdeteksi"]) & set(r["benar"])) for r in rows)
    fp = sum(len(set(r["terdeteksi"]) - set(r["benar"])) for r in rows)
    fn = sum(len(set(r["benar"]) - set(r["terdeteksi"])) for r in rows)
    return tp / max(tp + fp, 1), tp / max(tp + fn, 1), len(rows)


def kumpulkan():
    f = dict(KONSTAN)
    git = lambda *a: subprocess.run(["git", "-C", str(AKAR), *a], capture_output=True, text=True).stdout.strip()  # noqa: E731
    f["jumlah_commit"] = int(git("rev-list", "--count", "HEAD"))
    f["mulai"] = git("log", "--reverse", "--format=%ad", "--date=short").splitlines()[0]
    lat = _json("ml/reports/latensi.json")
    f["latensi_detik"] = round(lat["waktu_s"])
    f["ram_mb"] = lat["rss_maks_mb"]
    f["cpu"] = "prosesor " + lat["mesin"].split(",")[0].replace(" 4-core", " (4 inti)")
    f["sim"] = _json("docs/assets/data/simulasi_lokasi.json")
    f["spesies"] = sorted(_json("ml/data/species_list.json"), key=lambda s: s["scientific_name"])

    cv = _json("ml/reports/eval_bersarang.json")
    f["cv"] = {"f1": cv["aggregat"]["f1_macro"], "acc": cv["aggregat"]["acc"],
               "f1_ci": (cv["ci95"]["f1_macro"]["ci95_low"], cv["ci95"]["f1_macro"]["ci95_high"]),
               "acc_ci": (cv["ci95"]["acc"]["ci95_low"], cv["ci95"]["acc"]["ci95_high"]),
               "n": cv["n_xc"], "n_non_xc": cv["n_non_xc"], "grup": cv["n_grup_perekam"],
               "p_ambang": cv["aggregat_pada_ambang"]["presisi"], "r_ambang": cv["aggregat_pada_ambang"]["recall"]}

    ind = _json("ml/reports/uji_independen.json")
    f["ind"] = {"acc": ind["jendela_terbaik"]["acc"], "f1": ind["jendela_terbaik"]["f1_macro"], "ci": tuple(ind["jendela_terbaik"]["ci95_acc"]),
                "n": ind["n_klip"]}

    e = _json("docs/assets/data/e2e_produksi_385147c.json")
    rows = e["per_berkas"]
    per = lambda k: [r for r in rows if r["korpus"] == k]  # noqa: E731
    peng = per("field/other")
    lapor = [r for r in peng if r.get("bagian") == "lapor"]
    f["e2e"] = {
        "n": len(rows), "gagal": len(e.get("gagal", [])),
        "target": _metrik([r for r in rows if r["korpus"] != "field/other"]),
        "semua": (e["agregat"]["presisi"], e["agregat"]["recall"]),
        "xc": _metrik(per("field/xc_noisy")), "inat": _metrik(per("field/inat")),
        "ind": _metrik(per("uji_independen")),
        "peng_n": len(peng), "peng_fp": sum(1 for r in peng if r["terdeteksi"]),
        "lapor_n": len(lapor), "lapor_fp": sum(1 for r in lapor if r["terdeteksi"]),
        "fp_menit": e["per_korpus"]["field/other"]["deteksi_palsu_per_menit"],
        "nontarget": e["spesies_nontarget_per_berkas"],
    }
    f1 = _json("docs/assets/diagrams/f1_per_spesies.json")["per_spesies"]
    f["f1_spesies"] = f1
    f["terlemah"] = sorted(f1.items(), key=lambda kv: kv[1])[:3]
    f["terkuat"] = max(f1.items(), key=lambda kv: kv[1])
    return f


if __name__ == "__main__":
    import pprint
    d = kumpulkan()
    d.pop("spesies")
    pprint.pprint(d, width=110)
