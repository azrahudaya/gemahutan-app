#!/usr/bin/env python3
"""Pemindai rahasia GemaHutan.

Ambil semua nilai dari berkas rahasia lokal (.env, deploy/.env.prod,
~/.kaggle/kaggle.json, berkas token Hugging Face di Downloads kalau ada), lalu
cari nilai itu di berkas yang akan dipublikasikan ke repo publik.

Yang dicetak HANYA nama berkas dan nama kunci, TIDAK PERNAH nilainya. Nilai
contoh pengembangan (minioadmin, gemahutan, us-east-1, dan semacamnya) diabaikan.

Pakai:
    python3 ops/pindai_rahasia.py <daftar-berkas>...
    python3 ops/pindai_rahasia.py --cwd <dir>   # pindai seluruh berkas git di dir

Keluar 0 kalau bersih, 1 kalau ada kecocokan.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

EXAMPLE_VALUES = {
    "", "minioadmin", "gemahutan", "us-east-1", "change-me-in-production", "test-secret",
    "secret", "your-xeno-canto-api-key", "your-kaggle-api-token", "ganti-dengan-string-acak-panjang",
}
SENSITIVE_NAME = re.compile(r"(?:secret|password|token|api[_-]?key|private|access[_-]?key|credential)", re.I)


def sumber_rahasia() -> list[Path]:
    """Berkas lokal yang berisi nilai rahasia untuk dicari."""
    hasil = [Path(".env"), Path("deploy/.env.prod"), Path.home() / ".kaggle/kaggle.json"]
    hasil.extend((Path.home() / "Downloads").glob("*huggingface*"))
    return [p for p in hasil if p.is_file()]


def kumpulkan_nilai(sumber: list[Path]) -> list[tuple[str, str]]:
    """Kembalikan pasangan (label, nilai) yang sensitif, non-contoh, panjang >= 8."""
    keluar: list[tuple[str, str]] = []
    for path in sumber:
        teks = path.read_text(encoding="utf-8", errors="ignore")
        if path.suffix == ".json":
            try:
                data = json.loads(teks)
            except json.JSONDecodeError:
                continue
            pasangan = data.items()
        else:
            pasangan = []
            for baris in teks.splitlines():
                if "=" not in baris:
                    continue
                k, v = baris.split("=", 1)
                pasangan.append((k.strip(), v.strip().strip('"').strip("'")))
        for k, v in pasangan:
            v = str(v)
            if SENSITIVE_NAME.search(k) and v not in EXAMPLE_VALUES and len(v) >= 8:
                keluar.append((f"{path.name}:{k}", v))
    return keluar


def cari(berkas: Path, nilai: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Cari nilai di satu berkas. Kembalikan (nama_berkas, nama_kunci) yang cocok."""
    try:
        isi = berkas.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []
    temuan: list[tuple[str, str]] = []
    for label, nilai_str in nilai:
        if nilai_str in isi:
            temuan.append((str(berkas), label))
    if re.search(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----", isi):
        temuan.append((str(berkas), "private-key-pattern"))
    return temuan


def daftar_berkas_git(cwd: Path) -> list[Path]:
    """Semua berkas yang dilacak git di cwd, kecuali .artifacts/."""
    keluar = subprocess.check_output(["git", "-C", str(cwd), "ls-files"], text=True).splitlines()
    hasil = []
    for rel in keluar:
        p = cwd / rel
        if ".artifacts/" in rel:
            continue
        if p.is_file():
            hasil.append(p)
    return hasil


def main() -> int:
    ap = argparse.ArgumentParser(description="Pemindai rahasia GemaHutan (cetak nama saja)")
    ap.add_argument("berkas", nargs="*", help="berkas yang dipindai (opsional)")
    ap.add_argument("--cwd", help="pindai seluruh berkas git di direktori ini")
    args = ap.parse_args()

    nilai = kumpulkan_nilai(sumber_rahasia())
    if not nilai:
        print("tidak ada nilai sensitif lokal yang ditemukan untuk dibandingkan")
        return 0

    target: list[Path] = [Path(b) for b in args.berkas]
    if args.cwd:
        target = daftar_berkas_git(Path(args.cwd))
    if not target:
        print("tidak ada berkas untuk dipindai")
        return 0

    semua: set[tuple[str, str]] = set()
    for berkas in target:
        for b, k in cari(berkas, nilai):
            semua.add((b, k))
    if semua:
        for b, k in sorted(semua):
            print(f"TEMUAN {b}: {k}")
        return 1
    print(f"BERSIH: {len(target)} berkas dipindai terhadap {len(nilai)} nilai sensitif lokal.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
