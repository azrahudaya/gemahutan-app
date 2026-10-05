"""Sapu konfigurasi cascade putaran 2: filter deteksi lemah.

Menimpa cascade.yaml, jalankan evaluasi_e2e.py, catat metrik per konfigurasi.
Output: ml/reports/sapu_cascade2.json + sapu_cascade2.md

Fokus: menekan deteksi palsu (butir 6) ke <=15%. Putaran 1 membuktikan
hanya trackb_wajib_birdnet yang berpengaruh (44% -> 21,6%). Putaran ini
menyapu filter _buang_deteksi_lemah: min_kemunculan_ulang, ambang_kuat,
min_durasi_s.

Jalankan: source .venv/bin/activate && python ml/sapu_cascade2.py
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
CASCADE_BAK = ROOT / "ml" / "configs" / "cascade_sapu2_bak.yaml"
REPORTS = ROOT / "ml" / "reports"
E2E_JSON = REPORTS / "e2e.json"
OUT_JSON = REPORTS / "sapu_cascade2.json"
OUT_MD = REPORTS / "sapu_cascade2.md"
CACHE_E2E = ROOT / "ml" / "data" / "cache_e2e"

# (label, wajib_bn, ambang_nontarget, margin, min_ulang, ambang_kuat, min_durasi)
KONFIGURASI = [
    ("base-wajib", True, 0.1, 0.0, 2, 0.5, 1.0),   # acuan: wajib_bn saja
    ("ulang3", True, 0.1, 0.0, 3, 0.5, 1.0),        # butuh muncul 3x
    ("ulang4", True, 0.1, 0.0, 4, 0.5, 1.0),        # butuh muncul 4x
    ("kuat06", True, 0.1, 0.0, 2, 0.6, 1.0),        # ambang kuat naik
    ("kuat07", True, 0.1, 0.0, 2, 0.7, 1.0),        # ambang kuat lebih tinggi
    ("durasi2", True, 0.1, 0.0, 2, 0.5, 2.0),       # min durasi 2 detik
    ("ulang3-kuat06", True, 0.1, 0.0, 3, 0.6, 1.0),  # kombinasi
    ("ulang3-kuat07", True, 0.1, 0.0, 3, 0.7, 1.0),  # kombinasi agresif
]


def metrik_dari_e2e(data: dict) -> dict:
    ag = data.get("agregat", {})
    per_korpus = data.get("per_korpus", {})

    other = per_korpus.get("field/other", {})
    n_other = other.get("n_berkas", 0)
    berkas_fp = other.get("berkas_dengan_deteksi_target", 0)
    det_palsu_pm = other.get("deteksi_palsu_per_menit", None)
    det_palsu_frac = round(berkas_fp / n_other, 4) if n_other > 0 else None

    inat = per_korpus.get("field/inat", {})
    xc = per_korpus.get("field/xc_noisy", {})
    indep = per_korpus.get("uji_independen", {})

    return {
        "presisi": ag.get("presisi"),
        "recall": ag.get("recall"),
        "deteksi_palsu_frac": det_palsu_frac,
        "deteksi_palsu_berkas": berkas_fp,
        "n_berkas_other": n_other,
        "deteksi_palsu_pm": det_palsu_pm,
        "phone_presisi": inat.get("presisi"),
        "phone_recall": inat.get("recall"),
        "xc_presisi": xc.get("presisi"),
        "xc_recall": xc.get("recall"),
        "indep_presisi": indep.get("presisi"),
        "indep_recall": indep.get("recall"),
    }


def tulis_cascade_yaml(wajib, ambang_nt, margin, min_ulang, ambang_kuat, min_durasi):
    teks = f"""# SEMENTARA — ditimpa oleh ml/sapu_cascade2.py.
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


def hapus_cache_e2e():
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
        print(f"[{i+1}/{len(KONFIGURASI)}] {label}: ulang={min_ulang}, "
              f"kuat={ambang_kuat}, durasi={min_durasi}")
        print(f"{'='*70}")

        tulis_cascade_yaml(wajib, ambang_nt, margin, min_ulang, ambang_kuat, min_durasi)
        hapus_cache_e2e()

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
            print(f"  GAGAL (exit {proc.returncode}): {proc.stderr[-300:]}")
            continue

        e2e = json.loads(E2E_JSON.read_text()) if E2E_JSON.exists() else None
        if e2e is None:
            hasil.append({"label": label, "error": "e2e.json missing",
                          "elapsed_s": round(elapsed, 1)})
            continue

        m = metrik_dari_e2e(e2e)
        hasil.append({"label": label, "min_ulang": min_ulang,
                      "ambang_kuat": ambang_kuat, "min_durasi": min_durasi,
                      "elapsed_s": round(elapsed, 1), **m})
        print(f"  P={m['presisi']}, R={m['recall']}, "
              f"DetPalsu={m['deteksi_palsu_frac']} ({m['deteksi_palsu_berkas']}/{m['n_berkas_other']}), "
              f"PhoneP={m['phone_presisi']}, PhoneR={m['phone_recall']}, "
              f"XC_R={m['xc_recall']}, Waktu={elapsed:.0f}s")

    if CASCADE_BAK.exists():
        CASCADE_BAK.rename(CASCADE_YAML)

    total = time.time() - t0
    OUT_JSON.write_text(json.dumps({
        "dijalankan": datetime.now(UTC).isoformat(),
        "total_elapsed_s": round(total, 1),
        "konfigurasi": hasil,
    }, indent=2, ensure_ascii=False))

    md = ["# Sapu Cascade Putaran 2 (filter deteksi lemah)", "",
          f"Dijalankan: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}",
          f"Total: {total/60:.1f} menit", "",
          "| Label | Ulang | Kuat | Durasi | P | R | DetPalsu | PhoneP | PhoneR | XC_R |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for h in hasil:
        if "error" in h:
            md.append(f"| {h['label']} | - | - | - | GAGAL | - | - | - | - | - |")
        else:
            md.append(f"| {h['label']} | {h['min_ulang']} | {h['ambang_kuat']} | "
                      f"{h['min_durasi']} | {h['presisi']} | {h['recall']} | "
                      f"{h['deteksi_palsu_frac']} | {h['phone_presisi']} | "
                      f"{h['phone_recall']} | {h['xc_recall']} |")
    OUT_MD.write_text("\n".join(md) + "\n")

    print(f"\nOutput: {OUT_JSON}")
    print(f"Output: {OUT_MD}")
    return 0


if __name__ == "__main__":
    sys.exit(main())