"""Promosikan checkpoint dari ml/runs/<id> ke ml/checkpoints/.

Hanya satu penulis ml/checkpoints/ yang sah. Semua skrip latih menulis ke
ml/runs/; skrip ini yang memindahkan setelah gerbang G lulus.

Pakai:
    python3 ml/promosikan.py --run ml/runs/20260927-120000

Gerbang G (dibaca dari ml/runs/<id>/gerbang.json):
    - F1 luar tidak lebih rendah dari baseline di luar CI
    - Independen tidak turun > 0.02
    - FP e2e pengecoh tidak naik
    - Tidak ada spesies turun recall > 0.15
    - Test penjaga lulus

Prosedur:
    1. Baca gerbang.json, pastikan semua gate lulus
    2. Backup ml/checkpoints/ ke ml/backups/<tanggal>-<sha8>/
    3. Salin best_model.npz, normalization.npz, label_map.json, meta.json
    4. Tulis MANIFEST.json (sha256 semua berkas, git SHA, perintah, versi)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ML_DIR = ROOT / "ml"
CHECKPOINTS = ML_DIR / "checkpoints"
BACKUPS = ML_DIR / "backups"
MANIFEST = CHECKPOINTS / "MANIFEST.json"

FILES_TO_PROMOTE = [
    "best_model.npz",
    "normalization.npz",
    "label_map.json",
    "meta.json",
]


CASCADE_CONFIG = ML_DIR / "configs" / "cascade.yaml"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _sha_cascade() -> str:
    """sha256 ml/configs/cascade.yaml, atau 'none' kalau tidak ada."""
    if CASCADE_CONFIG.exists():
        return sha256_file(CASCADE_CONFIG)
    return "none"


def get_git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, timeout=5
        ).strip()
    except Exception:
        return "unknown"


def baca_gerbang(run_dir: Path) -> dict:
    """Baca gerbang.json, kembalikan dict. SystemExit kalau tidak ada atau gagal."""
    gerbang_path = run_dir / "gerbang.json"
    if not gerbang_path.exists():
        print(f"ERROR: {gerbang_path} tidak ditemukan. Jalankan evaluasi gerbang dulu.")
        raise SystemExit(1)
    try:
        g = json.loads(gerbang_path.read_text())
    except json.JSONDecodeError as e:
        print(f"ERROR: {gerbang_path} bukan JSON valid: {e}")
        raise SystemExit(1) from e
    return g


def baca_pengecualian(path: Path) -> list[str]:
    """Baca berkas pengecualian, kembalikan daftar nama kriteria yang dilewati.

    Format berkas: {"kriteria": "<nama>", "disetujui_oleh": ..., "tanggal": ...,
    "alasan": ...}. `kriteria` boleh string tunggal atau daftar. Hanya kriteria
    yang disebut di sini yang dilewati; logika gerbang tidak diubah.
    """
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as e:
        print(f"ERROR: tidak bisa membaca berkas pengecualian {path}: {e}")
        raise SystemExit(1) from e
    kriteria = data.get("kriteria", [])
    if isinstance(kriteria, str):
        kriteria = [kriteria]
    return list(kriteria)


def cek_gerbang(g: dict, dikecualikan: list[str] | None = None) -> bool:
    """Periksa semua gate di gerbang.json. Kembalikan True kalau semua lulus.

    Kriteria yang namanya ada di `dikecualikan` dilewati dan dicatat, bukan
    dipaksa lulus. Gerbang lain tetap diperiksa apa adanya.
    """
    nama_dikecualikan = set(dikecualikan or [])
    semua_lulus = True
    for nama, hasil in g.items():
        if nama == "pengecualian":
            continue
        if nama in nama_dikecualikan:
            print(f"  LEWAT (pengecualian disetujui): {nama}")
            continue
        lulus = hasil.get("lulus", hasil.get("pass", False))
        if not lulus:
            print(f"  GAGAL: {nama}")
            semua_lulus = False
        else:
            print(f"  OK: {nama}")
    if not semua_lulus:
        print("\nGerbang G tidak lulus. Promosi dibatalkan.")
    return semua_lulus


def backup_checkpoints(timestamp: str) -> Path:
    """Salin ml/checkpoints/ ke ml/backups/<timestamp>-<sha8>/."""
    # Dapatkan sha256 pendek dari checkpoint saat ini
    ckpt = CHECKPOINTS / "best_model.npz"
    if ckpt.exists():
        sha8 = sha256_file(ckpt)[:8]
    else:
        sha8 = "empty"
    dest = BACKUPS / f"{timestamp}-{sha8}"
    dest.mkdir(parents=True, exist_ok=True)
    for f in CHECKPOINTS.iterdir():
        if f.is_file() and f.name != "MANIFEST.json":
            shutil.copy2(f, dest / f.name)
    print(f"Backup: {CHECKPOINTS} -> {dest}")
    # Verifikasi
    for f in FILES_TO_PROMOTE:
        src = CHECKPOINTS / f
        dst = dest / f
        if src.exists() and dst.exists():
            if sha256_file(src) != sha256_file(dst):
                print(f"  ERROR: sha256 {f} tidak cocok setelah backup!")
                raise SystemExit(1)
    print("  sha256 verified")
    return dest


def promote(run_dir: Path) -> None:
    """Salin artefak dari run_dir ke ml/checkpoints/."""
    for f in FILES_TO_PROMOTE:
        src = run_dir / f
        dst = CHECKPOINTS / f
        if not src.exists():
            print(f"  WARNING: {src} tidak ditemukan, dilewati")
            continue
        shutil.copy2(src, dst)
        print(f"  {f}: copied")

    # Verifikasi sha256
    for f in FILES_TO_PROMOTE:
        src = run_dir / f
        dst = CHECKPOINTS / f
        if src.exists() and dst.exists():
            if sha256_file(src) != sha256_file(dst):
                print(f"  ERROR: sha256 {f} tidak cocok setelah salin!")
                raise SystemExit(1)
    print("  sha256 verified")


def tulis_manifest(run_dir: Path, pengecualian: dict | None = None) -> None:
    """Tulis MANIFEST.json dengan sha256 semua berkas, plus catatan pengecualian."""
    manifest = {
        "generated_utc": datetime.utcnow().isoformat() + "Z",
        "git_sha": get_git_sha(),
        "source_run": str(run_dir.relative_to(ROOT)),
        "files": {},
        "cascade_config_sha256": _sha_cascade(),
    }
    if pengecualian is not None:
        manifest["pengecualian"] = pengecualian
    for f in sorted(CHECKPOINTS.iterdir()):
        if f.is_file() and f.name != "MANIFEST.json":
            manifest["files"][f.name] = {
                "sha256": sha256_file(f),
                "size_bytes": f.stat().st_size,
            }

    # Tambahkan info dari meta.json kalau ada
    meta_path = CHECKPOINTS / "meta.json"
    if meta_path.exists():
        meta = json.loads(meta_path.read_text())
        manifest["build_command"] = meta.get("config", "unknown")
        manifest["model_type"] = meta.get("model_type", "unknown")
        manifest["numpy_version"] = meta.get("numpy_version", "unknown")

    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    print(f"MANIFEST: {MANIFEST}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Promosikan checkpoint ke produksi")
    parser.add_argument("--run", required=True, help="Direktori run sumber, e.g. ml/runs/20260927-120000")
    parser.add_argument("--pengecualian", help="Berkas JSON pengecualian kriteria gerbang")
    args = parser.parse_args()

    run_dir = Path(args.run)
    if not run_dir.is_absolute():
        run_dir = ROOT / run_dir
    if not run_dir.exists():
        print(f"ERROR: {run_dir} tidak ditemukan")
        return 1

    pengecualian = None
    dikecualikan: list[str] = []
    if args.pengecualian:
        pengecualian = json.loads(Path(args.pengecualian).read_text())
        dikecualikan = baca_pengecualian(Path(args.pengecualian))
        print(f"Pengecualian: {dikecualikan}")

    # 1. Baca dan cek gerbang
    print(f"Gerbang G dari {run_dir}:")
    g = baca_gerbang(run_dir)
    if not cek_gerbang(g, dikecualikan):
        return 1

    # 2. Backup
    timestamp = datetime.now().strftime("%Y-%m-%d")
    print("\nBackup...")
    backup_checkpoints(timestamp)

    # 3. Promosi
    print("\nPromosi...")
    promote(run_dir)

    # 4. Manifest
    print("\nManifest...")
    tulis_manifest(run_dir, pengecualian)

    print("\nPromosi selesai.")
    print(f"Checkpoint sha256: {sha256_file(CHECKPOINTS / 'best_model.npz')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())