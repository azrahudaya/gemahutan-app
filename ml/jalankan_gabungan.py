"""Jalankan kandidat GABUNGAN G lewat jalur e2e produksi, tanpa menyentuh produksi.

G = K2 (29 klip ND dibuang) + K3 (jendela bersuara) + K1 (konfirmasi lunak 0,9).

Catatan penting soal komposisi: K2 dan K3 TIDAK perlu digabung sebagai dua
langkah terpisah. Sudah diperiksa ke berkas, bukan diasumsikan:
ml/configs/k3_bersuara.yaml memakai splits_file ml/data/splits_v3_nd_bersih.json,
yaitu splits yang 29 klip ND-nya sudah dibuang (8229 -> 8200 klip latih, selisih
persis sama dengan daftar di ml/data/klip_nd_dibuang.json). Jadi model K3 SUDAH
memuat K2 di dalamnya, dan G = model K3 + kebijakan K1.

TIGA JEBAKAN yang dihindari di sini, semuanya pernah memakan korban di repo ini:

1. cascade.yaml produksi TIDAK ditulis. Konfigurasi kandidat ditulis ke
   ml/runs/<id>/cascade.yaml dan dipakai lewat GEMAHUTAN_CASCADE_CONFIG. Sapuan
   lama menimpa berkas produksi lalu memulihkannya dengan git checkout, dan itu
   meninggalkan jendela waktu tempat berkas produksi berisi kebijakan
   eksperimen.

2. Cache e2e WAJIB direktori terpisah. ml/evaluasi_e2e.py meng-key cache hanya
   dari path berkas audio (baris 207), tanpa sha256 checkpoint atau konfigurasi.
   Memakai cache bawaan berarti kandidat membaca deteksi milik baseline dan
   melaporkannya sebagai hasil sendiri, tanpa satu pun pesan error.

3. Env var di-set SEBELUM subprocess dijalankan. ml/engines/embedding_clf.py
   membaca GEMAHUTAN_CHECKPOINT_DIR sekali saat impor, jadi menyetelnya di dalam
   proses yang sudah mengimpor modul itu tidak berpengaruh (bug yang diperbaiki
   di commit 888a430). Karena e2e dijalankan sebagai subprocess baru, env var
   memang terbaca.

Jalankan:
  .venv/bin/python ml/jalankan_gabungan.py --id g_k3_k1 --lunak 0.9
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ML = ROOT / "ml"
REP = ML / "reports"

# Kebijakan produksi, disalin dari ml/configs/cascade.yaml (sha256 5fc2d627).
# Ditulis eksplisit supaya kandidat berbeda dari produksi HANYA pada kunci yang
# memang diubah, bukan karena kunci bawaan yang hilang.
CASCADE_PRODUKSI = {
    "ambang_birdnet_nontarget": 0.1,
    "trackb_wajib_birdnet": False,
    "margin_top1_top2": 0.0,
    "pakai_energi": False,
    "ambang_energi": 0.0,
    "min_kemunculan_ulang": 2,
    "ambang_kuat": 0.5,
}


def metrik_berkas(rows: list[dict]) -> tuple[float, float]:
    """Presisi dan recall per deteksi. Disalin dari ops/audit_model.py:275."""
    tp = sum(len(set(r["terdeteksi"]) & set(r["benar"])) for r in rows)
    fp = sum(len(set(r["terdeteksi"]) - set(r["benar"])) for r in rows)
    fn = sum(len(set(r["benar"]) - set(r["terdeteksi"])) for r in rows)
    return tp / max(tp + fp, 1), tp / max(tp + fn, 1)


def ringkas(e2e: dict) -> dict:
    """Hitung metrik bagian pilih dan lapor dengan definisi audit."""
    rows = e2e.get("per_berkas", [])
    out = {}

    pilih = [r for r in rows if r.get("bagian") == "pilih"]
    peng_p = [r for r in pilih if r["korpus"] == "field/other"]
    targ_p = [r for r in pilih if r["korpus"] in ("field/inat", "field/xc_noisy")]
    out["pilih"] = {
        "n_pengecoh": len(peng_p),
        "fp_berkas": sum(1 for r in peng_p if r["terdeteksi"]),
        "fp_rate": round(sum(1 for r in peng_p if r["terdeteksi"]) / max(len(peng_p), 1), 4),
        "n_target": len(targ_p),
        "recall_target": round(
            sum(1 for r in targ_p if set(r["terdeteksi"]) & set(r["benar"])) / max(len(targ_p), 1), 4),
    }

    lapor = [r for r in rows if r.get("bagian") == "lapor"]
    peng_l = [r for r in lapor if r["korpus"] == "field/other"]
    targ_l = [r for r in rows if r["korpus"] != "field/other"
              and (r.get("bagian") == "lapor" or r["korpus"] == "uji_independen")]
    inat_l = [r for r in lapor if r["korpus"] == "field/inat"]

    fp_l = sum(1 for r in peng_l if r["terdeteksi"]) / max(len(peng_l), 1)
    _, rec_l = metrik_berkas(targ_l)
    p_in, r_in = metrik_berkas(inat_l)
    out["lapor"] = {
        "n_pengecoh": len(peng_l),
        "c13_fp_pengecoh_berkas": round(fp_l, 4),
        "c13_recall_target": round(rec_l, 4),
        "c13_n_target": len(targ_l),
        "c13_lulus_nilai8": bool(fp_l <= 0.15 and rec_l >= 0.70),
        "c13_lulus_nilai7": bool(fp_l <= 0.25 and rec_l >= 0.65),
        "c15_inat_presisi": round(p_in, 4),
        "c15_inat_recall": round(r_in, 4),
        "c15_n_inat": len(inat_l),
        "c15_lulus": bool(p_in >= 0.75 and r_in >= 0.62),
    }
    out["pool"] = e2e.get("pool", {})
    out["sha256_checkpoint"] = e2e.get("sha256_checkpoint")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", required=True, help="nama run, dipakai sebagai ml/runs/<id>")
    ap.add_argument("--ckpt", default=str(ML / "runs" / "k3_bersuara_model"))
    ap.add_argument("--emb-dir", default=str(ML / "embeddings_bersuara_v3_klip"))
    ap.add_argument("--lunak", type=float, default=0.9,
                    help="trackb_konfirmasi_skor_min_lunak (K1). 0 = tanpa K1")
    ap.add_argument("--thresholds", default=str(REP / "thresholds.json"),
                    help="berkas ambang per spesies. Bawaan = ambang PRODUKSI")
    ap.add_argument("--timeout", type=int, default=1800)
    a = ap.parse_args()

    import yaml

    run_dir = ML / "runs" / a.id
    run_dir.mkdir(parents=True, exist_ok=True)
    cache_dir = run_dir / "cache_e2e"

    cfg = dict(CASCADE_PRODUKSI)
    if a.lunak > 0:
        cfg["trackb_wajib_birdnet"] = True
        cfg["trackb_konfirmasi_skor_min_lunak"] = a.lunak
    cfg_path = run_dir / "cascade.yaml"
    cfg_path.write_text(yaml.dump(cfg, default_flow_style=False, sort_keys=True))

    ckpt = Path(a.ckpt)
    if not (ckpt / "best_model.npz").exists():
        print(f"ERROR: best_model.npz tidak ada di {ckpt}")
        return 1

    sha_cascade_produksi = hashlib.sha256(
        (ML / "configs" / "cascade.yaml").read_bytes()).hexdigest()[:16]

    env = dict(os.environ)
    env["GEMAHUTAN_CHECKPOINT_DIR"] = str(ckpt)
    env["GEMAHUTAN_EMB_DIR"] = str(a.emb_dir)
    env["GEMAHUTAN_CASCADE_CONFIG"] = str(cfg_path)
    env["GEMAHUTAN_THRESHOLDS_FILE"] = str(a.thresholds)

    out_e2e = run_dir / "e2e.json"
    print(f"run        : {a.id}")
    print(f"checkpoint : {ckpt}")
    print(f"emb_dir    : {a.emb_dir}")
    print(f"cascade    : {cfg_path} (lunak={a.lunak})")
    print(f"thresholds : {a.thresholds}")
    print(f"cache      : {cache_dir} (TERPISAH, bukan cache produksi)")
    print(f"cascade.yaml produksi sha256 (harus tetap 5fc2d62743e5b35f): {sha_cascade_produksi}")

    t0 = time.time()
    hasil = subprocess.run(
        [sys.executable, str(ML / "evaluasi_e2e.py"),
         "--out-json", str(out_e2e), "--cache-dir", str(cache_dir)],
        cwd=str(ROOT), env=env, capture_output=True, text=True, timeout=a.timeout,
    )
    dt = time.time() - t0
    if hasil.returncode != 0:
        print(f"e2e GAGAL setelah {dt:.0f}s")
        print(hasil.stdout[-2000:])
        print(hasil.stderr[-2000:])
        return 1

    e2e = json.loads(out_e2e.read_text())
    ring = ringkas(e2e)
    ring["id"] = a.id
    ring["waktu_e2e_s"] = round(dt, 1)
    ring["config_cascade"] = cfg
    ring["checkpoint_dir"] = str(ckpt)
    ring["thresholds_file"] = str(a.thresholds)
    ring["sha256_cascade_produksi_setelah_run"] = hashlib.sha256(
        (ML / "configs" / "cascade.yaml").read_bytes()).hexdigest()[:16]

    out_json = REP / "gabungan" / f"{a.id}.json"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(ring, indent=2, ensure_ascii=False))

    p, lap = ring["pilih"], ring["lapor"]
    print(f"\nselesai {dt:.0f}s")
    print(f"PILIH  FP {p['fp_rate']} ({p['fp_berkas']}/{p['n_pengecoh']})  "
          f"recall {p['recall_target']} (n={p['n_target']})")
    print(f"LAPOR  C13 FP {lap['c13_fp_pengecoh_berkas']} recall {lap['c13_recall_target']}  "
          f"nilai7 {'ya' if lap['c13_lulus_nilai7'] else 'TIDAK'}  "
          f"nilai8 {'ya' if lap['c13_lulus_nilai8'] else 'TIDAK'}")
    print(f"       C15 P {lap['c15_inat_presisi']} R {lap['c15_inat_recall']}  "
          f"{'LULUS' if lap['c15_lulus'] else 'gagal'}")
    print(f"Ditulis: {out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
