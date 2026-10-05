"""Sapu konfigurasi cascade v3: hanya bagian "pilih" dari pembagian_openset.json.

Aturan ML_00: pemilihan hanya di bagian "pilih", evaluasi akhir di bagian "lapor".
Bagian "lapor" dihitung sekali untuk baseline dan konfigurasi terbaik.

Output: ml/reports/sapu_cascade_v3.json + sapu_cascade_v3.md
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CASCADE_YAML = ROOT / "ml" / "configs" / "cascade.yaml"
CASCADE_BAK = ROOT / "ml" / "configs" / "cascade_v3_bak.yaml"
REPORTS = ROOT / "ml" / "reports"
E2E_JSON = REPORTS / "e2e.json"
OUT_JSON = REPORTS / "sapu_cascade_v3.json"
OUT_MD = REPORTS / "sapu_cascade_v3.md"
CACHE_E2E = ROOT / "ml" / "data" / "cache_e2e"

KONFIGURASI = [
    ("baseline", False, 0.1, 0.0, 2, 0.5, 1.0),
    ("wajib-bn-010", True, 0.1, 0.0, 2, 0.5, 1.0),
    ("kuat06", True, 0.1, 0.0, 2, 0.6, 1.0),
    ("kuat07", True, 0.1, 0.0, 2, 0.7, 1.0),
    ("ulang3-kuat06", True, 0.1, 0.0, 3, 0.6, 1.0),
]


def metrik_pilih(data: dict) -> dict:
    """Hitung metrik hanya dari baris bagian: 'pilih'."""
    per_berkas = data.get("per_berkas", [])
    subset = [b for b in per_berkas if b.get("bagian") == "pilih"]

    # Agregat
    tp = fp = fn = 0.0
    for b in subset:
        benar_set = set(b["benar"])
        deteksi_set = set(b["terdeteksi"])
        tp += len(benar_set & deteksi_set)
        fp += len(deteksi_set - benar_set)
        fn += len(benar_set - deteksi_set)
    presisi = round(tp / (tp + fp), 4) if (tp + fp) > 0 else 0.0
    recall = round(tp / (tp + fn), 4) if (tp + fn) > 0 else 0.0

    # Per korpus
    per_korpus = {}
    for korpus_name in ["field/inat", "field/xc_noisy", "field/other", "uji_independen"]:
        sub = [b for b in subset if b["korpus"] == korpus_name]
        if not sub:
            continue
        if korpus_name == "field/other":
            total_menit = sum(b.get("durasi_s", 0) for b in sub) / 60.0
            fp_count = sum(len(b["terdeteksi"]) for b in sub)
            berkas_fp = sum(1 for b in sub if b["terdeteksi"])
            per_korpus[korpus_name] = {
                "deteksi_palsu_per_menit": round(fp_count / total_menit, 4) if total_menit > 0 else 0.0,
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
    xc = per_korpus.get("field/xc_noisy", {})

    return {
        "presisi": presisi,
        "recall": recall,
        "n_pilih": len(subset),
        "phone_presisi": inat.get("presisi"),
        "phone_recall": inat.get("recall"),
        "deteksi_palsu_frac": other.get("deteksi_palsu_frac"),
        "deteksi_palsu_berkas": other.get("berkas_dengan_deteksi_target"),
        "n_berkas_other": other.get("n_berkas", 0),
        "xc_presisi": xc.get("presisi"),
        "xc_recall": xc.get("recall"),
    }


def tulis_cascade_yaml(wajib, ambang_nt, margin, min_ulang, ambang_kuat, min_durasi):
    teks = f"""# SEMENTARA — ditimpa oleh ml/sapu_cascade_v3.py.
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


def hapus_cache():
    if CACHE_E2E.exists():
        shutil.rmtree(CACHE_E2E)
        CACHE_E2E.mkdir(parents=True)


def main() -> int:
    if CASCADE_YAML.exists() and not CASCADE_BAK.exists():
        CASCADE_YAML.rename(CASCADE_BAK)

    hasil = []
    t0 = time.time()

    for i, (label, wajib, ambang_nt, margin, min_ulang, ambang_kuat, min_durasi) in enumerate(KONFIGURASI):
        print(f"\n{'='*70}")
        print(f"[{i+1}/{len(KONFIGURASI)}] {label}: wajib={wajib}, "
              f"kuat={ambang_kuat}, ulang={min_ulang}")
        print(f"{'='*70}")

        tulis_cascade_yaml(wajib, ambang_nt, margin, min_ulang, ambang_kuat, min_durasi)
        hapus_cache()

        t1 = time.time()
        proc = subprocess.run(
            [sys.executable, "ml/evaluasi_e2e.py"],
            cwd=ROOT, capture_output=True, text=True, timeout=1800,
            env={**os.environ, "TF_CPP_MIN_LOG_LEVEL": "3"},
        )
        elapsed = time.time() - t1

        if proc.returncode != 0:
            hasil.append({"label": label, "error": f"exit {proc.returncode}",
                          "elapsed_s": round(elapsed, 1)})
            print(f"  GAGAL (exit {proc.returncode})")
            continue

        e2e = json.loads(E2E_JSON.read_text()) if E2E_JSON.exists() else None
        if e2e is None:
            hasil.append({"label": label, "error": "e2e.json missing",
                          "elapsed_s": round(elapsed, 1)})
            continue

        m = metrik_pilih(e2e)
        hasil.append({"label": label, "wajib_bn": wajib,
                      "ambang_kuat": ambang_kuat, "min_ulang": min_ulang,
                      "elapsed_s": round(elapsed, 1), **m})
        print(f"  P={m['presisi']}, R={m['recall']}, "
              f"DetPalsu={m['deteksi_palsu_frac']} ({m['deteksi_palsu_berkas']}/{m['n_berkas_other']}), "
              f"PhoneP={m['phone_presisi']}, PhoneR={m['phone_recall']}, "
              f"n_pilih={m['n_pilih']}, Waktu={elapsed:.0f}s")

    if CASCADE_BAK.exists():
        CASCADE_BAK.rename(CASCADE_YAML)

    total = time.time() - t0
    OUT_JSON.write_text(json.dumps({
        "dijalankan": datetime.now(UTC).isoformat(),
        "total_elapsed_s": round(total, 1),
        "subset": "pilih (pembagian_openset.json)",
        "konfigurasi": hasil,
    }, indent=2, ensure_ascii=False))

    md = ["# Sapu Cascade v3 (subset pilih)", "",
          f"Dijalankan: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}",
          f"Total: {total/60:.1f} menit, subset: bagian pilih dari pembagian_openset.json",
          "",
          "| Label | Wajib BN | Kuat | Ulang | P | R | DetPalsu | PhoneP | PhoneR | n_pilih |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for h in hasil:
        if "error" in h:
            md.append(f"| {h['label']} | - | - | - | GAGAL | - | - | - | - | - |")
        else:
            md.append(f"| {h['label']} | {h['wajib_bn']} | {h['ambang_kuat']} | "
                      f"{h['min_ulang']} | {h['presisi']} | {h['recall']} | "
                      f"{h['deteksi_palsu_frac']} | {h['phone_presisi']} | "
                      f"{h['phone_recall']} | {h['n_pilih']} |")

    # Catatan selisih spesies
    md.append("")
    md.append("## Selisih spesies pengecoh")
    md.append("pembagian_openset.json: 14 pilih + 15 lapor = 29 spesies.")
    md.append("field/other: 22 spesies (21 dari 29 pembagian + 1 target"
              " Arachnothera longirostra).")
    md.append("8 spesies pembagian tidak punya klip di field/other:")
    md.append("pilih (2): Acridotheres javanicus, Streptopelia bitorquata;")
    md.append("lapor (6): Halcyon cyanoventris, Megalaima armillaris,"
              " Megalaima javensis, Nectarinia jugularis, Oriolus chinensis,"
              " Zosterops palpebrosus.")
    md.append("Tidak mengubah pembagian (file beku).")

    OUT_MD.write_text("\n".join(md) + "\n")

    print(f"\nOutput: {OUT_JSON}")
    print(f"Output: {OUT_MD}")
    return 0


if __name__ == "__main__":
    sys.exit(main())