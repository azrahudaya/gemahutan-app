"""Sapu konfigurasi cascade: mengukur deteksi palsu untuk tiap kombinasi parameter.

Menimpa cascade.yaml, jalankan evaluasi_e2e.py, catat metrik per konfigurasi.
Output: ml/reports/sapu_cascade.json + sapu_cascade.md

Digunakan untuk butir 6: menekan deteksi palsu ke <=15%.
Jalankan: source .venv/bin/activate && python ml/sapu_cascade.py
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CASCADE_YAML = ROOT / "ml" / "configs" / "cascade.yaml"
CASCADE_BAK = ROOT / "ml" / "configs" / "cascade_sapu_bak.yaml"
REPORTS = ROOT / "ml" / "reports"
E2E_JSON = REPORTS / "e2e.json"
OUT_JSON = REPORTS / "sapu_cascade.json"
OUT_MD = REPORTS / "sapu_cascade.md"

# Konfigurasi yang disapu
KONFIGURASI = [
    # (label, trackb_wajib_birdnet, ambang_birdnet_nontarget, margin_top1_top2)
    ("baseline", False, 0.1, 0.0),
    ("wajib-bn-010", True, 0.1, 0.0),
    ("wajib-bn-020", True, 0.2, 0.0),
    ("wajib-bn-010-margin-01", True, 0.1, 0.1),
    ("wajib-bn-020-margin-01", True, 0.2, 0.1),
    ("wajib-bn-030", True, 0.3, 0.0),
]


def baca_e2e() -> dict | None:
    if not E2E_JSON.exists():
        return None
    return json.loads(E2E_JSON.read_text())


def metrik_dari_e2e(data: dict) -> dict:
    """Ekstrak metrik kunci dari e2e.json."""
    ag = data.get("agregat", {})
    per_korpus = data.get("per_korpus", {})

    # False detection pada pengecoh (field/other)
    other = per_korpus.get("field/other", {})
    false_det_other_pm = other.get("deteksi_palsu_per_menit", None)
    false_det_other_berkas = other.get("berkas_dengan_deteksi_target", None)
    false_det_other_n = other.get("n_berkas", None)
    false_det_frac = None
    if false_det_other_berkas is not None and false_det_other_n is not None and false_det_other_n > 0:
        false_det_frac = round(false_det_other_berkas / false_det_other_n, 4)

    # Phone (field/inat)
    inat = per_korpus.get("field/inat", {})
    phone_p = inat.get("presisi", None)
    phone_r = inat.get("recall", None)

    return {
        "presisi": ag.get("presisi"),
        "recall": ag.get("recall"),
        "spesies_nontarget_per_berkas": ag.get("spesies_nontarget_per_berkas"),
        "deteksi_palsu_per_menit": false_det_other_pm,
        "deteksi_palsu_berkas": false_det_other_berkas,
        "deteksi_palsu_frac": false_det_frac,
        "n_berkas_other": false_det_other_n,
        "phone_presisi": phone_p,
        "phone_recall": phone_r,
    }


def tulis_cascade_yaml(trackb_wajib: bool, ambang_nontarget: float, margin: float):
    teks = f"""# SEMENTARA — ditimpa oleh ml/sapu_cascade.py.
# Konfigurasi CascadeEngine (Track A BirdNET + Track B classifier).

ambang_birdnet_nontarget: {ambang_nontarget}
trackb_wajib_birdnet: {'true' if trackb_wajib else 'false'}
margin_top1_top2: {margin}
pakai_energi: false
ambang_energi: 0.0
min_kemunculan_ulang: 2
ambang_kuat: 0.5
"""
    CASCADE_YAML.write_text(teks)


def hapus_cache_e2e():
    """Hapus cache deteksi final supaya cascade config baru diterapkan."""
    import shutil
    cache_dir = ROOT / "ml" / "data" / "cache_e2e"
    if cache_dir.exists():
        shutil.rmtree(cache_dir)
        cache_dir.mkdir(parents=True)
        print(f"  Cache e2e dihapus: {cache_dir}")


def main() -> int:
    # Backup cascade.yaml asli
    if CASCADE_YAML.exists() and not CASCADE_BAK.exists():
        CASCADE_YAML.rename(CASCADE_BAK)
        print(f"Backup: {CASCADE_YAML} -> {CASCADE_BAK}")
    elif CASCADE_YAML.exists():
        CASCADE_YAML.write_text(CASCADE_BAK.read_text())

    hasil = []
    t0 = time.time()

    for i, (label, wajib, ambang, margin) in enumerate(KONFIGURASI):
        print(f"\n{'='*60}")
        print(f"[{i+1}/{len(KONFIGURASI)}] {label}: wajib_bn={wajib}, "
              f"ambang_nontarget={ambang}, margin={margin}")
        print(f"{'='*60}")

        tulis_cascade_yaml(wajib, ambang, margin)
        hapus_cache_e2e()

        t1 = time.time()
        proc = subprocess.run(
            [sys.executable, "ml/evaluasi_e2e.py"],
            cwd=ROOT,
            capture_output=True, text=True, timeout=1800,
            env={**__import__("os").environ, "TF_CPP_MIN_LOG_LEVEL": "3"},
        )
        elapsed = time.time() - t1

        if proc.returncode != 0:
            print(f"GAGAL (exit {proc.returncode})")
            print(proc.stderr[-500:] if proc.stderr else "(no stderr)")
            hasil.append({
                "label": label, "wajib_bn": wajib, "ambang_nontarget": ambang,
                "margin": margin, "error": f"exit {proc.returncode}",
                "elapsed_s": round(elapsed, 1),
            })
            continue

        e2e = baca_e2e()
        if e2e is None:
            hasil.append({
                "label": label, "wajib_bn": wajib, "ambang_nontarget": ambang,
                "margin": margin, "error": "e2e.json not found",
                "elapsed_s": round(elapsed, 1),
            })
            continue

        m = metrik_dari_e2e(e2e)
        entry = {
            "label": label,
            "wajib_bn": wajib,
            "ambang_nontarget": ambang,
            "margin": margin,
            "elapsed_s": round(elapsed, 1),
            **m,
        }
        hasil.append(entry)
        print(f"  Presisi={m['presisi']}, Recall={m['recall']}, "
              f"DetPalsu={m['deteksi_palsu_frac']} ({m['deteksi_palsu_berkas']}/{m['n_berkas_other']}), "
              f"PhoneP={m['phone_presisi']}, PhoneR={m['phone_recall']}, "
              f"Waktu={elapsed:.0f}s")

    # Pulihkan cascade.yaml asli
    if CASCADE_BAK.exists():
        CASCADE_BAK.rename(CASCADE_YAML)
        print(f"\nDipulihkan: {CASCADE_YAML}")

    total_elapsed = time.time() - t0

    # Tulis output
    OUT_JSON.write_text(json.dumps({
        "dijalankan": datetime.now(UTC).isoformat(),
        "total_elapsed_s": round(total_elapsed, 1),
        "konfigurasi": hasil,
    }, indent=2, ensure_ascii=False))

    # Tulis markdown
    md = ["# Sapu Konfigurasi Cascade",
          "",
          f"Dijalankan: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}",
          f"Total waktu: {total_elapsed/60:.1f} menit",
          "",
          "| Label | Wajib BN | Ambang NT | Margin | Presisi | Recall | DetPalsu | Phone P | Phone R | Waktu |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for h in hasil:
        if "error" in h:
            md.append(f"| {h['label']} | {h['wajib_bn']} | {h['ambang_nontarget']} | "
                      f"{h['margin']} | GAGAL | - | - | - | - | {h['elapsed_s']}s |")
        else:
            md.append(
                f"| {h['label']} | {h['wajib_bn']} | {h['ambang_nontarget']} | "
                f"{h['margin']} | {h['presisi']} | {h['recall']} | "
                f"{h.get('deteksi_palsu_frac', '-')} | {h['phone_presisi']} | "
                f"{h['phone_recall']} | {h['elapsed_s']}s |"
            )
    OUT_MD.write_text("\n".join(md) + "\n")

    print(f"\nOutput: {OUT_JSON}")
    print(f"Output: {OUT_MD}")
    return 0


if __name__ == "__main__":
    sys.exit(main())