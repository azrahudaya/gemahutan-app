"""Eksperimen: apakah klip verifikasi baru yang menurunkan metrik, atau ekstraksi ulang.

Membandingkan dua konfigurasi identik (300 epoch, hidden 256, lr 0.001):
  A. manifest 1370 klip asli (tanpa klip hasil verifikasi)
  B. manifest 1371 klip (dengan ver-116)

Hasil ditulis ke stdout. Semua artefak asli dicadangkan lebih dulu.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path("/home/fuudaya/Projects/gemahutan")
ML = REPO / "ml"
DATA = ML / "data"
EMB = ML / "embeddings"
CKPT = ML / "checkpoints"
REPORTS = ML / "reports"
PY = REPO / ".venv" / "bin" / "python"


def backup():
    for path in [EMB / "embeddings.npy", EMB / "labels.npy", EMB / "clip_ids.json",
                 EMB / "label_map.json", CKPT / "best_model.npz", CKPT / "meta.json",
                 CKPT / "normalization.npz", REPORTS / "metrics.json", REPORTS / "eval.md",
                 REPORTS / "thresholds.json", DATA / "manifest.csv", DATA / "splits.json"]:
        if path.exists():
            shutil.copy2(path, str(path) + ".expbak")
    print("cadangan dibuat")


def restore():
    for path in [EMB / "embeddings.npy", EMB / "labels.npy", EMB / "clip_ids.json",
                 EMB / "label_map.json", CKPT / "best_model.npz", CKPT / "meta.json",
                 CKPT / "normalization.npz", REPORTS / "metrics.json", REPORTS / "eval.md",
                 REPORTS / "thresholds.json", DATA / "manifest.csv", DATA / "splits.json"]:
        bak = Path(str(path) + ".expbak")
        if bak.exists():
            shutil.copy2(bak, path)
    print("dipulihkan dari cadangan")


def set_manifest(include_verified: bool):
    rows = (DATA / "manifest.csv").read_text().splitlines()
    header, body = rows[0], rows[1:]
    if include_verified:
        kept = body
    else:
        kept = [r for r in body if not r.startswith("ver-")]
    (DATA / "manifest.csv").write_text("\n".join([header] + kept) + "\n")

    splits = json.loads((DATA / "splits.json").read_text())
    for key in ("train", "val", "test"):
        splits[key] = [c for c in splits[key] if include_verified or not c.startswith("ver-")]
    (DATA / "splits.json").write_text(json.dumps(splits, indent=2))
    return len(kept)


def train_and_report(label: str):
    result = subprocess.run(
        [str(PY), "data/extract_embeddings.py", "--force"], cwd=ML,
        capture_output=True, text=True,
    )
    print(f"[{label}] ekstraksi: {result.stdout.strip().splitlines()[-1] if result.stdout else 'gagal'}")

    result = subprocess.run(
        [str(PY), "train.py", "--epochs", "300", "--hidden", "256", "--lr", "0.001"],
        cwd=ML, capture_output=True, text=True,
    )
    tail = [line for line in result.stdout.splitlines() if "val_acc" in line]
    print(f"[{label}] val_acc terakhir: {tail[-1].strip() if tail else 'tidak ada'}")
    meta = json.loads((CKPT / "meta.json").read_text())
    print(f"[{label}] best_val_acc: {meta['best_val_acc']:.4f}")
    return meta["best_val_acc"]


def main():
    backup()
    try:
        n = set_manifest(include_verified=False)
        print(f"Konfigurasi A: {n} klip (tanpa hasil verifikasi)")
        val_a = train_and_report("A")

        n = set_manifest(include_verified=True)
        print(f"Konfigurasi B: {n} klip (dengan hasil verifikasi)")
        val_b = train_and_report("B")

        print("\nHASIL")
        print(f"  A tanpa klip verifikasi : best_val_acc {val_a:.4f}")
        print(f"  B dengan klip verifikasi: best_val_acc {val_b:.4f}")
        print(f"  selisih: {val_b - val_a:+.4f}")
    finally:
        # Kembalikan artefak konfigurasi A (tanpa verifikasi) sebagai kondisi repo,
        # supaya model yang dipakai aplikasi tetap yang terbaik.
        set_manifest(include_verified=False)
        subprocess.run([str(PY), "data/extract_embeddings.py", "--force"], cwd=ML, capture_output=True)
        subprocess.run([str(PY), "train.py", "--epochs", "300", "--hidden", "256", "--lr", "0.001"],
                       cwd=ML, capture_output=True)
        subprocess.run([str(PY), "evaluate.py"], cwd=ML, capture_output=True)
        meta = json.loads((CKPT / "meta.json").read_text())
        print(f"\nKondisi akhir repo: manifest tanpa verifikasi, best_val_acc {meta['best_val_acc']:.4f}")


if __name__ == "__main__":
    sys.exit(main())
