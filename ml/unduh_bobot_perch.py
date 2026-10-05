"""Unduh bobot resmi Perch dari Kaggle Models lewat kagglehub.

Kenapa ada: `ml/embeddings_perch/` hasil sesi lama (24 Sep) tapi folder bobot
`ml/models_perch/` TIDAK ADA di mesin ini, jadi angka Perch belum bisa
direproduksi dan uji independen K6 belum bisa diekstrak. Skrip ini mengambil
SavedModel resmi dan membuat symlink `ml/models_perch` ke lokasi cache, supaya
`ml/data/extract_perch.py` bisa dipakai tanpa diubah.

Varian dicoba berurutan: perch_v2 lebih dulu karena embedding sesi lama 1536
dimensi, yang cocok dengan Perch 2.0 (Perch 1.x memberi 1280).

Jalankan: .venv-perch/bin/python3 ml/unduh_bobot_perch.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TUJUAN = REPO / "ml" / "models_perch"
LAPORAN = REPO / "ml" / "reports" / "k6_perch" / "bobot_perch.json"

VARIAN = [
    "google/bird-vocalization-classifier/tensorFlow2/perch_v2",
    "google/bird-vocalization-classifier/tensorFlow2/bird-vocalization-classifier",
]


def main() -> int:
    import kagglehub

    hasil = {"dicoba": [], "terpakai": None}
    jalur = None
    for handle in VARIAN:
        try:
            jalur = Path(kagglehub.model_download(handle))
            hasil["dicoba"].append({"handle": handle, "status": "ok", "path": str(jalur)})
            hasil["terpakai"] = handle
            break
        except Exception as exc:  # noqa: BLE001 - alasan gagal ditulis apa adanya
            hasil["dicoba"].append({"handle": handle, "status": "gagal", "error": str(exc)[:400]})

    if jalur is None:
        LAPORAN.parent.mkdir(parents=True, exist_ok=True)
        LAPORAN.write_text(json.dumps(hasil, indent=2, ensure_ascii=False))
        print("GAGAL: tidak ada varian yang bisa diunduh")
        print(json.dumps(hasil, indent=2, ensure_ascii=False))
        return 1

    # SavedModel bisa berada satu tingkat di dalam folder unduhan.
    akar = jalur
    if not (akar / "saved_model.pb").exists():
        kandidat = sorted(akar.rglob("saved_model.pb"))
        if kandidat:
            akar = kandidat[0].parent
    hasil["saved_model_dir"] = str(akar)
    hasil["ada_saved_model_pb"] = (akar / "saved_model.pb").exists()
    hasil["isi"] = sorted(p.name for p in akar.iterdir())[:30]
    hasil["ukuran_mb"] = round(
        sum(p.stat().st_size for p in akar.rglob("*") if p.is_file()) / 1e6, 1
    )

    if TUJUAN.is_symlink() or TUJUAN.exists():
        print(f"CATATAN: {TUJUAN} sudah ada, tidak diubah")
    else:
        TUJUAN.symlink_to(akar)
        print(f"symlink {TUJUAN} -> {akar}")

    LAPORAN.parent.mkdir(parents=True, exist_ok=True)
    LAPORAN.write_text(json.dumps(hasil, indent=2, ensure_ascii=False))
    print(json.dumps(hasil, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
