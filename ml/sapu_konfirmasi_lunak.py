"""Sapuan konfirmasi lunak (S1).

Konfigurasi baru: trackb_konfirmasi_skor_min_lunak (threshold konfirmasi lunak).
Kalau Track B confidence >= threshold ini, skip konfirmasi BirdNET.

Jalankan:
  python3 ml/sapu_konfirmasi_lunak.py
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

    phone_pilih = [b for b in pilih if b.get("korpus") == "field/inat"]
    phone_tp = sum(1 for b in phone_pilih if any(d in b.get("benar", []) for d in b.get("terdeteksi", [])))
    phone_recall = phone_tp / len(phone_pilih) if phone_pilih else 0
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


AMBANG_BAWAAN = [0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99]


def main():
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--ambang", type=float, nargs="+", default=AMBANG_BAWAAN,
        help="daftar ambang konfirmasi lunak yang disapu",
    )
    ap.add_argument(
        "--akhiran", default="",
        help="akhiran nama berkas keluaran, supaya sapuan halus tidak "
             "menimpa hasil sapuan kasar yang sudah di-commit",
    )
    args = ap.parse_args()
    ambang_list = args.ambang
    akhiran = args.akhiran

    pembagian = muat_pembagian()

    # Snapshot per konfigurasi disimpan di sini. Tanpa ini, data per berkas
    # hilang karena e2e.json ditimpa konfigurasi berikutnya lalu dipulihkan ke
    # versi git di akhir, sehingga selang bootstrap (wajib ML_09) tidak bisa
    # dihitung tanpa menjalankan ulang seluruh sapuan.
    snap_dir = REPORTS / f"snapshots_s1{akhiran}"
    snap_dir.mkdir(parents=True, exist_ok=True)

    cascade_asli = CASCADE_FILE.read_text() if CASCADE_FILE.exists() else None

    # Konfigurasi konfirmasi lunak: trackb_konfirmasi_skor_min_lunak
    #
    # PENTING: konfirmasi lunak hanya berarti kalau ADA konfirmasi dasar yang
    # mau dilunakkan. trackb_wajib_birdnet=True adalah constraint paling ketat
    # dari sapu_konfirmasi.md (FP turun 0.42->0.20 tapi recall ikut turun
    # 0.80->0.64). Threshold lunak menentukan di confidence berapa Track B
    # boleh SKIP syarat wajib_birdnet itu. Tanpa wajib_birdnet=True aktif,
    # tidak ada apa pun untuk di-skip dan semua hasil akan identik baseline
    # (bug yang terjadi di percobaan pertama script ini).
    konfigurasi = [
        {"nama": "tanpa_konfirmasi", "trackb_wajib_birdnet": False,
         "trackb_konfirmasi_topk": 0, "trackb_konfirmasi_skor_min": 0.0,
         "trackb_konfirmasi_skor_min_lunak": 0.0},
        {"nama": "wajib_bn_keras", "trackb_wajib_birdnet": True,
         "trackb_konfirmasi_topk": 0, "trackb_konfirmasi_skor_min": 0.0,
         "trackb_konfirmasi_skor_min_lunak": 0.0},
    ]

    # Konfirmasi lunak: wajib_birdnet AKTIF, tapi di-skip kalau conf >= threshold.
    #
    # PERINGATAN PEMILIHAN: ambang di sini HANYA boleh dipilih memakai metrik
    # bagian pilih. Menyetelnya supaya angka bagian LAPOR pas di batas C13
    # adalah kebocoran yang membatalkan hasil (aturan ML_08). Angka lapor
    # dihitung sekali untuk konfigurasi terpilih dan ditulis terpisah.
    for threshold in ambang_list:
        konfigurasi.append({
            "nama": f"lunak_{threshold}",
            "trackb_wajib_birdnet": True,
            "trackb_konfirmasi_topk": 0,
            "trackb_konfirmasi_skor_min": 0.0,
            "trackb_konfirmasi_skor_min_lunak": threshold,
        })

    hasil = []
    total = len(konfigurasi)

    for i, cfg in enumerate(konfigurasi):
        nama = cfg.pop("nama")
        print(f"\n[{i + 1}/{total}] {nama}")

        if CACHE_E2E.exists():
            shutil.rmtree(CACHE_E2E)

        tulis_cascade_yaml(cfg)

        t0 = time.time()
        e2e = run_e2e()
        dt = time.time() - t0

        if e2e is None:
            print(f"  GAGAL ({dt:.0f}s)")
            hasil.append({"nama": nama, "status": "GAGAL"})
            continue

        # Simpan data per berkas SEKARANG, sebelum konfigurasi berikutnya
        # menimpa e2e.json. Ini yang dipakai ml/bootstrap_pilih.py.
        snap_path = snap_dir / f"e2e_{nama.replace('.', '')}.json"
        snap_path.write_text(json.dumps(e2e, ensure_ascii=False))

        metrik = hitung_metrik_pilih(e2e, pembagian)
        metrik["nama"] = nama
        metrik["config"] = cfg
        metrik["waktu_s"] = round(dt, 1)
        metrik["snapshot"] = str(snap_path.relative_to(ROOT))
        hasil.append(metrik)

        print(f"  FP pilih: {metrik['fp_berkas']}/{metrik['n_other_pilih']} ({metrik['fp_rate']})")
        print(f"  Recall target pilih: {metrik['recall_target']}")
        print(f"  Phone: P {metrik['phone_presisi']} R {metrik['phone_recall']}")
        print(f"  Waktu: {dt:.0f}s")

    # Kembalikan cascade.yaml ke versi git (bukan cuma string yang dibaca di
    # awal run ini -- kalau run sebelumnya gagal di tengah, cascade_asli bisa
    # saja sudah berisi versi yang korup, bukan versi produksi yang benar).
    import subprocess
    hasil_checkout = subprocess.run(
        ["git", "checkout", "--", str(CASCADE_FILE)], cwd=str(ROOT),
        capture_output=True, text=True,
    )
    if hasil_checkout.returncode != 0 and cascade_asli is not None:
        # Fallback kalau file belum pernah di-commit: tulis balik versi awal.
        CASCADE_FILE.write_text(cascade_asli)
    subprocess.run(["git", "checkout", "--", str(REPORTS / "e2e.json")], cwd=str(ROOT))

    out_path = REPORTS / f"sapu_konfirmasi_lunak{akhiran}.json"
    out_path.write_text(json.dumps(hasil, indent=2, ensure_ascii=False))
    print(f"\nHasil: {out_path}")

    md_lines = ["# Sapuan konfirmasi lunak (S1)",
                "",
                "Konfigurasi baru: `trackb_konfirmasi_skor_min_lunak`",
                "Kalau Track B confidence >= threshold ini, skip konfirmasi BirdNET.",
                "Metrik dihitung HANYA dari bagian pilih.",
                "",
                "| Konfigurasi | FP pilih | FP rate | Recall target | Phone P | Phone R | Waktu |",
                "|---|---:|---:|---:|---:|---:|---:|"]
    for h in hasil:
        if h.get("status") == "GAGAL":
            md_lines.append(f"| {h['nama']} | GAGAL | | | | | |")
            continue
        md_lines.append(
            f"| {h['nama']} | {h['fp_berkas']}/{h['n_other_pilih']} | {h['fp_rate']} | "
            f"{h['recall_target']} | {h['phone_presisi']} | {h['phone_recall']} | {h['waktu_s']}s |"
        )

    md_path = REPORTS / f"sapu_konfirmasi_lunak{akhiran}.md"
    md_path.write_text("\n".join(md_lines) + "\n")
    print(f"Laporan: {md_path}")


if __name__ == "__main__":
    main()
