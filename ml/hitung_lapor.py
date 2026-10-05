"""Hitung metrik bagian "lapor" sekali untuk baseline dan konfigurasi terpilih.

Aturan ML_00: pemilihan konfigurasi hanya di bagian "pilih". Angka "lapor"
dihitung sekali untuk konfigurasi terpilih dan baseline, ditulis terpisah.

Output: ml/reports/lapor_baseline_vs_terpilih.json + .md

Jalankan: source .venv/bin/activate && python ml/hitung_lapor.py
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CASCADE_YAML = ROOT / "ml" / "configs" / "cascade.yaml"
CASCADE_BAK = ROOT / "ml" / "configs" / "cascade_lapor_bak.yaml"
REPORTS = ROOT / "ml" / "reports"
E2E_JSON = REPORTS / "e2e.json"
OUT_JSON = REPORTS / "lapor_baseline_vs_terpilih.json"
OUT_MD = REPORTS / "lapor_baseline_vs_terpilih.md"
CACHE_E2E = ROOT / "ml" / "data" / "cache_e2e"

# (label, wajib_bn, ambang_nt, margin, min_ulang, ambang_kuat, min_durasi)
KONFIGURASI = [
    ("baseline", False, 0.1, 0.0, 2, 0.5, 1.0),
    ("terpilih_kuat06", True, 0.1, 0.0, 2, 0.6, 1.0),
]


def metrik_bagian(data: dict, bagian: str) -> dict:
    per_berkas = data.get("per_berkas", [])
    subset = [b for b in per_berkas if b.get("bagian") == bagian]

    tp = fp = fn = 0.0
    for b in subset:
        benar_set = set(b["benar"])
        deteksi_set = set(b["terdeteksi"])
        tp += len(benar_set & deteksi_set)
        fp += len(deteksi_set - benar_set)
        fn += len(benar_set - deteksi_set)
    presisi = round(tp / (tp + fp), 4) if (tp + fp) > 0 else 0.0
    recall = round(tp / (tp + fn), 4) if (tp + fn) > 0 else 0.0

    per_korpus = {}
    for korpus_name in ["field/inat", "field/xc_noisy", "field/other", "uji_independen"]:
        sub = [b for b in subset if b["korpus"] == korpus_name]
        if not sub:
            continue
        if korpus_name == "field/other":
            berkas_fp = sum(1 for b in sub if b["terdeteksi"])
            per_korpus[korpus_name] = {
                "berkas_dengan_deteksi_target": berkas_fp,
                "n_berkas": len(sub),
                "deteksi_palsu_frac": round(berkas_fp / len(sub), 4) if sub else 0.0,
            }
        else:
            k_tp = k_fp = k_fn = 0.0
            for b in sub:
                benar_set = set(b["benar"])
                deteksi_set = set(b["terdeteksi"])
                k_tp += len(benar_set & deteksi_set)
                k_fp += len(deteksi_set - benar_set)
                k_fn += len(benar_set - deteksi_set)
            per_korpus[korpus_name] = {
                "presisi": round(k_tp / (k_tp + k_fp), 4) if (k_tp + k_fp) > 0 else 0.0,
                "recall": round(k_tp / (k_tp + k_fn), 4) if (k_tp + k_fn) > 0 else 0.0,
                "n_berkas": len(sub),
            }

    inat = per_korpus.get("field/inat", {})
    other = per_korpus.get("field/other", {})
    return {
        "presisi": presisi,
        "recall": recall,
        "n_berkas": len(subset),
        "phone_presisi": inat.get("presisi"),
        "phone_recall": inat.get("recall"),
        "deteksi_palsu_frac": other.get("deteksi_palsu_frac"),
        "deteksi_palsu_berkas": other.get("berkas_dengan_deteksi_target"),
        "n_berkas_other": other.get("n_berkas", 0),
        "per_korpus": per_korpus,
    }


def tulis_cascade_yaml(wajib, ambang_nt, margin, min_ulang, ambang_kuat, min_durasi):
    teks = f"""# SEMENTARA — ditimpa oleh ml/hitung_lapor.py.
ambang_birdnet_nontarget: {ambang_nt}
trackb_wajib_birdnet: {'true' if wajib else 'false'}
margin_top1_top2: {margin}
pakai_energi: false
ambang_energi: 0.0
min_kemunculan_ulang: {min_ulang}
ambang_kuat: {ambang_kuat}
min_durasi_s: {min_durasi}
"""
    CASCADE_YAML.write_text(teks)


def main() -> int:
    if CASCADE_YAML.exists() and not CASCADE_BAK.exists():
        CASCADE_YAML.rename(CASCADE_BAK)

    hasil = {}
    for label, wajib, ambang_nt, margin, min_ulang, ambang_kuat, min_durasi in KONFIGURASI:
        print(f"\n=== {label} ===")
        tulis_cascade_yaml(wajib, ambang_nt, margin, min_ulang, ambang_kuat, min_durasi)
        if CACHE_E2E.exists():
            shutil.rmtree(CACHE_E2E)
            CACHE_E2E.mkdir(parents=True)

        subprocess.run(
            [sys.executable, "ml/evaluasi_e2e.py"],
            cwd=ROOT, capture_output=True, text=True, timeout=1800,
            env={**os.environ, "TF_CPP_MIN_LOG_LEVEL": "3"},
        )
        e2e = json.loads(E2E_JSON.read_text())
        lapor = metrik_bagian(e2e, "lapor")
        pilih = metrik_bagian(e2e, "pilih")
        hasil[label] = {"lapor": lapor, "pilih": pilih}
        print(f"  LAPOR: P={lapor['presisi']}, R={lapor['recall']}, "
              f"DetPalsu={lapor['deteksi_palsu_frac']} "
              f"({lapor['deteksi_palsu_berkas']}/{lapor['n_berkas_other']}), "
              f"PhoneR={lapor['phone_recall']}")
        print(f"  PILIH: P={pilih['presisi']}, R={pilih['recall']}, "
              f"DetPalsu={pilih['deteksi_palsu_frac']}")

    if CASCADE_BAK.exists():
        CASCADE_BAK.rename(CASCADE_YAML)

    OUT_JSON.write_text(json.dumps({
        "dijalankan": datetime.now(UTC).isoformat(),
        "catatan": "Angka lapor dihitung sekali untuk baseline dan konfigurasi terpilih.",
        "hasil": hasil,
    }, indent=2, ensure_ascii=False))

    md = ["# Angka Lapor: Baseline vs Terpilih", "",
          f"Dijalankan: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}",
          "", "## Bagian lapor (uji akhir, sekali hitung)", "",
          "| Konfigurasi | P | R | DetPalsu | PhoneP | PhoneR | n |",
          "|---|---|---|---|---|---|---|"]
    for label, h in hasil.items():
        lp = h["lapor"]
        md.append(f"| {label} | {lp['presisi']} | {lp['recall']} | "
                  f"{lp['deteksi_palsu_frac']} | {lp['phone_presisi']} | "
                  f"{lp['phone_recall']} | {lp['n_berkas']} |")
    md += ["", "## Bagian pilih (untuk perbandingan)", "",
           "| Konfigurasi | P | R | DetPalsu | PhoneP | PhoneR | n |",
           "|---|---|---|---|---|---|---|"]
    for label, h in hasil.items():
        pl = h["pilih"]
        md.append(f"| {label} | {pl['presisi']} | {pl['recall']} | "
                  f"{pl['deteksi_palsu_frac']} | {pl['phone_presisi']} | "
                  f"{pl['phone_recall']} | {pl['n_berkas']} |")
    OUT_MD.write_text("\n".join(md) + "\n")

    print(f"\nOutput: {OUT_JSON}")
    print(f"Output: {OUT_MD}")
    return 0


if __name__ == "__main__":
    sys.exit(main())