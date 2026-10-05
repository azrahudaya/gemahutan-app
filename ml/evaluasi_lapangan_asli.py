"""Evaluasi data lapangan asli dari database.

Membaca deteksi terverifikasi (bukan rekaman Xeno-canto) dari DB dan menulis
lapangan_asli.json. Hanya boleh dijalankan setelah manusia merekam dan
memverifikasi minimal 30 menit audio.

Jalankan: .venv/bin/python ml/evaluasi_lapangan_asli.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ML_DIR = ROOT / "ml"
REPORTS = ML_DIR / "reports"


def jalankan_sql(sql: str) -> str:
    hasil = subprocess.run(
        ["docker", "compose", "exec", "-T", "db", "psql", "-U", "gemahutan",
         "-d", "gemahutan", "-At", "-c", sql],
        cwd=ROOT, capture_output=True, text=True, timeout=60,
    )
    if hasil.returncode != 0:
        print(hasil.stderr.strip()[:400], file=sys.stderr)
        raise SystemExit(1)
    return hasil.stdout.strip()


def main() -> int:
    # Menit terverifikasi + jumlah deteksi terverifikasi (bukan XC)
    baris = jalankan_sql(
        "SELECT COALESCE(SUM(r.duration_s),0)/60.0, COUNT(DISTINCT d.id) "
        "FROM detections d JOIN recordings r ON r.id = d.recording_id "
        "WHERE d.verified_status <> 'unverified' "
        "AND COALESCE(r.original_filename, '') NOT LIKE 'xc-%'"
    )
    if not baris or "|" not in baris:
        print("Tidak ada data lapangan terverifikasi.")
        return 0
    menit, n = baris.split("|")
    menit = float(menit or 0)
    n = int(n or 0)

    # Presisi per spesies: benar / (benar + salah)
    presisi = {}
    baris_sp = jalankan_sql(
        "SELECT s.scientific_name, d.verified_status, COUNT(*) "
        "FROM detections d "
        "JOIN recordings r ON r.id = d.recording_id "
        "JOIN species s ON s.id = d.species_id "
        "WHERE d.verified_status <> 'unverified' "
        "AND COALESCE(r.original_filename, '') NOT LIKE 'xc-%' "
        "GROUP BY s.scientific_name, d.verified_status"
    )
    benar = {}
    salah = {}
    for line in baris_sp.splitlines():
        if "|" not in line:
            continue
        sp, status, cnt = line.split("|")
        cnt = int(cnt)
        if status == "correct":
            benar[sp] = benar.get(sp, 0) + cnt
        elif status == "incorrect":
            salah[sp] = salah.get(sp, 0) + cnt
    for sp in set(benar) | set(salah):
        tp = benar.get(sp, 0)
        fp = salah.get(sp, 0)
        presisi[sp] = round(tp / (tp + fp), 4) if (tp + fp) > 0 else 0.0

    out = {
        "menit_terverifikasi": round(menit, 1),
        "n_deteksi_terverifikasi": n,
        "presisi_per_spesies": presisi,
        "dibuat": datetime.now(UTC).isoformat(),
    }
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "lapangan_asli.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False))
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())