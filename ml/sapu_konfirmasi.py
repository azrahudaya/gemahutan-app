"""Sapuan konfirmasi BirdNET bertingkat (L6-3).

Menyapu kombinasi trackb_konfirmasi_topk (0,1,3,5,10) dan
trackb_konfirmasi_skor_min (0.0, 0.01, 0.02, 0.05, 0.1).
Metrik dihitung HANYA dari bagian pilih.

Jalankan:
  python3 ml/sapu_konfirmasi.py
"""
from __future__ import annotations

import json
import shutil
import sys
import time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

ML_DIR = ROOT / "ml"
CACHE_E2E = ML_DIR / "data" / "cache_e2e"
REPORTS = ML_DIR / "reports"
CONFIGS = ML_DIR / "configs"
CASCADE_FILE = CONFIGS / "cascade.yaml"
PEMBAGIAN_FILE = ML_DIR / "data" / "pembagian_openset.json"


def muat_pembagian():
    return json.loads(PEMBAGIAN_FILE.read_text())


def run_e2e():
    """Jalankan evaluasi e2e dan kembalikan hasilnya."""
    # evaluasi_e2e menulis ke ml/reports/e2e.json
    # Kita import dan jalankan secara programatik
    import importlib

    import ml.evaluasi_e2e as mod
    importlib.reload(mod)
    # Jalankan lewat subprocess supaya cascade config dibaca ulang
    import subprocess
    result = subprocess.run(
        [sys.executable, str(ML_DIR / "evaluasi_e2e.py")],
        capture_output=True, text=True, cwd=str(ROOT), timeout=600
    )
    if result.returncode != 0:
        print(f"e2e GAGAL: {result.stderr[-500:]}")
        return None
    return json.loads((REPORTS / "e2e.json").read_text())


def hitung_metrik_pilih(e2e_data, pembagian):
    """Hitung deteksi palsu dan recall target dari bagian pilih saja."""
    berkas = e2e_data.get("per_berkas", [])

    pilih = [b for b in berkas if b.get("bagian") == "pilih"]
    other_pilih = [b for b in pilih if b.get("korpus") == "field/other"]
    target_pilih = [b for b in pilih if b.get("korpus") in ("field/inat", "field/xc_noisy")]

    fp = sum(1 for b in other_pilih if len(b.get("terdeteksi", [])) > 0)
    fp_rate = fp / len(other_pilih) if other_pilih else 0

    tp = sum(1 for b in target_pilih if any(d in b.get("benar", []) for d in b.get("terdeteksi", [])))
    recall = tp / len(target_pilih) if target_pilih else 0

    # Ponsel (iNat) pilih
    phone_pilih = [b for b in pilih if b.get("korpus") == "field/inat"]
    phone_tp = sum(1 for b in phone_pilih if any(d in b.get("benar", []) for d in b.get("terdeteksi", [])))
    phone_recall = phone_tp / len(phone_pilih) if phone_pilih else 0
    # Presisi ponsel
    phone_det = sum(len(b.get("terdeteksi", [])) for b in phone_pilih)
    phone_correct = sum(
        len(set(b.get("terdeteksi", [])) & set(b.get("benar", [])))
        for b in phone_pilih
    )
    phone_prec = phone_correct / phone_det if phone_det else 0

    return {
        "n_other_pilih": len(other_pilih),
        "fp_berkas": fp,
        "fp_rate": round(fp_rate, 4),
        "n_target_pilih": len(target_pilih),
        "recall_target": round(recall, 4),
        "n_phone_pilih": len(phone_pilih),
        "phone_presisi": round(phone_prec, 4),
        "phone_recall": round(phone_recall, 4),
    }


def tulis_cascade_yaml(cfg: dict):
    """Tulis cascade.yaml sementara."""
    CASCADE_FILE.parent.mkdir(parents=True, exist_ok=True)
    CASCADE_FILE.write_text(yaml.dump(cfg, default_flow_style=False))


def main():
    pembagian = muat_pembagian()

    # Simpan cascade.yaml asli
    cascade_asli = CASCADE_FILE.read_text() if CASCADE_FILE.exists() else None

    # Baseline tanpa konfirmasi (baris wajib ML_07 A4)
    konfigurasi = [
        {"nama": "tanpa_konfirmasi", "trackb_wajib_birdnet": False,
         "trackb_konfirmasi_topk": 0, "trackb_konfirmasi_skor_min": 0.0},
        {"nama": "wajib_bn_saja", "trackb_wajib_birdnet": True,
         "trackb_konfirmasi_topk": 0, "trackb_konfirmasi_skor_min": 0.0},
    ]

    # Sapuan topk saja (skor_min=0)
    for k in [1, 3, 5, 10]:
        konfigurasi.append({
            "nama": f"topk_{k}",
            "trackb_wajib_birdnet": False,
            "trackb_konfirmasi_topk": k,
            "trackb_konfirmasi_skor_min": 0.0,
        })

    # Sapuan skor_min saja (topk=0)
    for s in [0.01, 0.02, 0.05, 0.1]:
        konfigurasi.append({
            "nama": f"skor_{s}",
            "trackb_wajib_birdnet": False,
            "trackb_konfirmasi_topk": 0,
            "trackb_konfirmasi_skor_min": s,
        })

    # Kombinasi wajib_bn + topk terbaik (untuk cek efek kumulatif)
    for k in [3, 5]:
        konfigurasi.append({
            "nama": f"wajib_bn_topk_{k}",
            "trackb_wajib_birdnet": True,
            "trackb_konfirmasi_topk": k,
            "trackb_konfirmasi_skor_min": 0.0,
        })

    hasil = []
    total = len(konfigurasi)

    for i, cfg in enumerate(konfigurasi):
        nama = cfg.pop("nama")
        print(f"\n[{i + 1}/{total}] {nama}")

        # Hapus cache e2e
        if CACHE_E2E.exists():
            shutil.rmtree(CACHE_E2E)

        # Tulis cascade.yaml
        tulis_cascade_yaml(cfg)

        t0 = time.time()
        e2e = run_e2e()
        dt = time.time() - t0

        if e2e is None:
            print(f"  GAGAL ({dt:.0f}s)")
            hasil.append({"nama": nama, "status": "GAGAL"})
            continue

        metrik = hitung_metrik_pilih(e2e, pembagian)
        metrik["nama"] = nama
        metrik["config"] = cfg
        metrik["waktu_s"] = round(dt, 1)
        hasil.append(metrik)

        print(f"  FP pilih: {metrik['fp_berkas']}/{metrik['n_other_pilih']} ({metrik['fp_rate']})")
        print(f"  Recall target pilih: {metrik['recall_target']}")
        print(f"  Phone: P {metrik['phone_presisi']} R {metrik['phone_recall']}")
        print(f"  Waktu: {dt:.0f}s")

    # Kembalikan cascade.yaml asli
    if cascade_asli is not None:
        CASCADE_FILE.write_text(cascade_asli)
    elif CASCADE_FILE.exists():
        CASCADE_FILE.unlink()

    # Kembalikan e2e.json asli (jangan biarkan tertulis dengan konfigurasi terakhir)
    import subprocess
    subprocess.run(["git", "checkout", "--", str(REPORTS / "e2e.json")], cwd=str(ROOT))

    # Tulis hasil
    out_path = REPORTS / "sapu_konfirmasi.json"
    out_path.write_text(json.dumps(hasil, indent=2, ensure_ascii=False))
    print(f"\nHasil: {out_path}")

    # Tulis laporan markdown
    md_lines = ["# Sapuan konfirmasi BirdNET bertingkat (L6-3)", "",
                 "Baseline = paket produksi. Metrik dihitung HANYA dari bagian pilih.", ""]
    md_lines.append("| Konfigurasi | FP pilih | FP rate | Recall target | Phone P | Phone R | Waktu |")
    md_lines.append("|---|---:|---:|---:|---:|---:|---:|")
    for h in hasil:
        if h.get("status") == "GAGAL":
            md_lines.append(f"| {h['nama']} | GAGAL | | | | | |")
            continue
        md_lines.append(
            f"| {h['nama']} | {h['fp_berkas']}/{h['n_other_pilih']} | {h['fp_rate']} | "
            f"{h['recall_target']} | {h['phone_presisi']} | {h['phone_recall']} | {h['waktu_s']}s |"
        )

    md_path = REPORTS / "sapu_konfirmasi.md"
    md_path.write_text("\n".join(md_lines) + "\n")
    print(f"Laporan: {md_path}")


if __name__ == "__main__":
    main()
