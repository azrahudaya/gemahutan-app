"""Selang kepercayaan bootstrap 95% untuk metrik bagian pilih (wajib ML_09).

ML_09 mewajibkan setiap angka yang dipakai MEMUTUSKAN disertai selang bootstrap
95%. Alasannya kuat: bagian pilih hanya berisi 59 berkas pengecoh, jadi satu
berkas menggeser angka deteksi palsu sekitar 1,7 poin dan dua konfigurasi bisa
terlihat berbeda padahal cuma kebetulan.

Yang di-resample adalah BERKAS, bukan deteksi. Itu unit percobaan yang benar:
satu berkas pengecoh menyumbang satu peluang deteksi palsu, dan deteksi di
dalam satu berkas saling berkorelasi sehingga me-resample deteksi akan
membuat selangnya terlalu sempit.

Metrik yang dihitung, semuanya HANYA dari baris `bagian == "pilih"`:
  fp_rate       berkas field/other yang punya minimal satu deteksi target
  recall_target berkas field/inat + field/xc_noisy yang terdeteksi benar
  phone_presisi, phone_recall pada field/inat

Pakai:
  python ml/bootstrap_pilih.py ml/reports/e2e.json
  python ml/bootstrap_pilih.py snapshot_a.json snapshot_b.json --nama baseline kandidat

Dengan dua berkas atau lebih, selisih antar konfigurasi juga di-bootstrap
berpasangan pada berkas yang sama, supaya pertanyaan "benar-benar lebih baik
atau cuma kebetulan" bisa dijawab.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

SEED = 2026
N_BOOT = 10000

KORPUS_TARGET = ("field/inat", "field/xc_noisy")


def muat_pilih(path: Path) -> list[dict]:
    d = json.loads(path.read_text())
    return [b for b in d.get("per_berkas", []) if b.get("bagian") == "pilih"]


def _indikator(baris: list[dict]) -> dict[str, dict[str, dict[str, float]]]:
    """Ubah tiap berkas jadi angka 0/1 per metrik, diindeks nama berkas.

    Disimpan per nama berkas supaya dua konfigurasi bisa dibandingkan pada
    berkas yang sama persis (bootstrap berpasangan).
    """
    other: dict[str, float] = {}
    target: dict[str, float] = {}
    phone_benar: dict[str, float] = {}
    phone_n_det: dict[str, float] = {}
    phone_n_cocok: dict[str, float] = {}

    for b in baris:
        nama = b.get("berkas", "")
        korpus = b.get("korpus")
        terdeteksi = set(b.get("terdeteksi", []))
        benar = set(b.get("benar", []))

        if korpus == "field/other":
            # Pengecoh: deteksi target apa pun adalah deteksi palsu.
            other[nama] = 1.0 if terdeteksi else 0.0
        if korpus in KORPUS_TARGET:
            target[nama] = 1.0 if (terdeteksi & benar) else 0.0
        if korpus == "field/inat":
            phone_benar[nama] = 1.0 if (terdeteksi & benar) else 0.0
            phone_n_det[nama] = float(len(terdeteksi))
            phone_n_cocok[nama] = float(len(terdeteksi & benar))

    return {
        "fp_rate": {"nilai": other},
        "recall_target": {"nilai": target},
        "phone_recall": {"nilai": phone_benar},
        "phone_presisi": {"pembilang": phone_n_cocok, "penyebut": phone_n_det},
    }


def _ringkas(nilai: np.ndarray, rng) -> tuple[float, float, float]:
    """Rerata + selang 95% dari resampling berkas."""
    n = len(nilai)
    if n == 0:
        return float("nan"), float("nan"), float("nan")
    idx = rng.integers(0, n, size=(N_BOOT, n))
    boot = nilai[idx].mean(axis=1)
    return (float(nilai.mean()),
            float(np.percentile(boot, 2.5)),
            float(np.percentile(boot, 97.5)))


def _ringkas_rasio(pembilang: np.ndarray, penyebut: np.ndarray, rng):
    """Presisi = total cocok / total deteksi, di-resample per berkas."""
    n = len(pembilang)
    if n == 0:
        return float("nan"), float("nan"), float("nan")
    titik = pembilang.sum() / penyebut.sum() if penyebut.sum() else float("nan")
    idx = rng.integers(0, n, size=(N_BOOT, n))
    atas = pembilang[idx].sum(axis=1)
    bawah = penyebut[idx].sum(axis=1)
    sah = bawah > 0
    boot = atas[sah] / bawah[sah]
    if boot.size == 0:
        return float(titik), float("nan"), float("nan")
    return (float(titik),
            float(np.percentile(boot, 2.5)),
            float(np.percentile(boot, 97.5)))


def hitung(path: Path) -> dict:
    baris = muat_pilih(path)
    ind = _indikator(baris)
    rng = np.random.default_rng(SEED)
    hasil = {"berkas": str(path), "n_pilih": len(baris)}

    for nama in ("fp_rate", "recall_target", "phone_recall"):
        d = ind[nama]["nilai"]
        arr = np.array([d[k] for k in sorted(d)], dtype=float)
        titik, lo, hi = _ringkas(arr, rng)
        hasil[nama] = {"n": len(arr), "titik": round(titik, 4),
                       "ci95": [round(lo, 4), round(hi, 4)]}

    p = ind["phone_presisi"]
    kunci = sorted(p["penyebut"])
    atas = np.array([p["pembilang"][k] for k in kunci], dtype=float)
    bawah = np.array([p["penyebut"][k] for k in kunci], dtype=float)
    titik, lo, hi = _ringkas_rasio(atas, bawah, rng)
    hasil["phone_presisi"] = {"n": len(kunci), "titik": round(titik, 4),
                             "ci95": [round(lo, 4), round(hi, 4)]}
    return hasil


def selisih(path_a: Path, path_b: Path, nama_a: str, nama_b: str) -> dict:
    """Bootstrap berpasangan: selisih b dikurangi a pada berkas yang sama."""
    ind_a = _indikator(muat_pilih(path_a))
    ind_b = _indikator(muat_pilih(path_b))
    rng = np.random.default_rng(SEED)
    out: dict[str, object] = {
        "a": nama_a, "b": nama_b, "metode": "bootstrap berpasangan per berkas",
    }

    for metrik in ("fp_rate", "recall_target", "phone_recall"):
        da, db = ind_a[metrik]["nilai"], ind_b[metrik]["nilai"]
        sama = sorted(set(da) & set(db))
        if not sama:
            continue
        va = np.array([da[k] for k in sama], dtype=float)
        vb = np.array([db[k] for k in sama], dtype=float)
        d = vb - va
        n = len(d)
        idx = rng.integers(0, n, size=(N_BOOT, n))
        boot = d[idx].mean(axis=1)
        lo, hi = np.percentile(boot, [2.5, 97.5])
        out[metrik] = {
            "n_berkas_sama": n,
            "selisih": round(float(d.mean()), 4),
            "ci95": [round(float(lo), 4), round(float(hi), 4)],
            # Selang yang memuat nol berarti belum terbukti beda.
            "beda_nyata": not (lo <= 0.0 <= hi),
        }
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("berkas", nargs="+", help="satu atau lebih e2e.json")
    ap.add_argument("--nama", nargs="*", default=None, help="label tiap berkas")
    ap.add_argument("--out", default=None, help="tulis JSON ke sini")
    a = ap.parse_args()

    paths = [Path(x) for x in a.berkas]
    for p in paths:
        if not p.exists():
            print(f"ERROR: {p} tidak ada")
            return 1
    nama = a.nama if a.nama and len(a.nama) == len(paths) else [p.stem for p in paths]

    laporan = {"n_bootstrap": N_BOOT, "seed": SEED, "per_konfigurasi": []}
    for p, nm in zip(paths, nama, strict=True):
        h = hitung(p)
        h["nama"] = nm
        laporan["per_konfigurasi"].append(h)
        print(f"\n=== {nm}  (n pilih {h['n_pilih']})")
        for metrik in ("fp_rate", "recall_target", "phone_presisi", "phone_recall"):
            v = h[metrik]
            print(f"  {metrik:14s} {v['titik']:.4f}  CI95 [{v['ci95'][0]:.4f}, {v['ci95'][1]:.4f}]  n={v['n']}")

    if len(paths) >= 2:
        laporan["selisih"] = []
        for i in range(1, len(paths)):
            s = selisih(paths[0], paths[i], nama[0], nama[i])
            laporan["selisih"].append(s)
            print(f"\n=== selisih {nama[i]} dikurangi {nama[0]}")
            for metrik in ("fp_rate", "recall_target", "phone_recall"):
                if metrik not in s:
                    continue
                v = s[metrik]
                tanda = "BEDA NYATA" if v["beda_nyata"] else "belum terbukti beda"
                print(f"  {metrik:14s} {v['selisih']:+.4f}  CI95 [{v['ci95'][0]:+.4f}, {v['ci95'][1]:+.4f}]  {tanda}")

    if a.out:
        Path(a.out).write_text(json.dumps(laporan, indent=2, ensure_ascii=False))
        print(f"\nDitulis: {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
