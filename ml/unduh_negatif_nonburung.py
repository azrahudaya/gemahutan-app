"""Unduh contoh negatif non-burung XC: belalang/jangkrik (Orthoptera) + kelelawar.

Pengganti 558 klip iNat serangga dan mamalia. Maksimal 600 klip.
Aturan sama dengan unduh_negatif_xc.py: kualitas A/B/C, lisensi non-ND,
1 req/detik, cache, berhenti kalau disk < 6 GB.

Output: ml/data/negatif_xc_nonburung/ + ml/data/manifest_negatif_nonburung.csv

Jalankan: source .venv/bin/activate && python ml/unduh_negatif_nonburung.py
"""
from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent
ML = ROOT / "ml"
DATA = ML / "data"
CACHE_DIR = DATA / "cache_api"
AUDIO_DIR = DATA / "negatif_xc_nonburung"
MANIFEST_OUT = DATA / "manifest_negatif_nonburung.csv"

XC_API = "https://xeno-canto.org/api/3/recordings"
XC_API_KEY = os.environ.get("XC_API_KEY", "").strip()
DELAY = 1.1
MAKS_KLIP = 600
GRUP = ["grasshoppers", "bats"]
NEGARA = ["indonesia", "malaysia", "singapore", "brunei", "philippines", "thailand"]


def lisensi_aman(lic: str) -> bool:
    if not lic:
        return False
    low = lic.lower().strip().rstrip("/")
    if "sampling+" in low:
        return False
    bagian = [p for p in low.split("/") if p]
    if not bagian:
        return False
    tail = bagian[-1]
    if tail.replace(".", "").isdigit() and len(bagian) >= 2:
        tail = bagian[-2]
    tokens = tail.replace("-", " ").replace("_", " ").split()
    return "nd" not in tokens


def cari(grup: str, negara: str, page: int = 1) -> dict | None:
    cache_file = CACHE_DIR / f"xc3_nb_{grup}_{negara}_p{page}.json"
    if cache_file.exists():
        return json.loads(cache_file.read_text())
    query = f"cnt:{negara} grp:{grup}"
    qs = urllib.parse.urlencode({"query": query, "key": XC_API_KEY, "page": str(page)})
    try:
        req = Request(f"{XC_API}?{qs}")
        with urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        print(f"  {grup}/{negara} hal {page} gagal: {e}")
        return None
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps(data, ensure_ascii=False))
    time.sleep(DELAY)
    return data


def unduh(xc_id: int, out_path: Path, max_attempts: int = 2) -> bool:
    """Unduh klip XC non-burung.

    Rekaman belalang/kelelawar sering WAV 96 kHz stereo (puluhan MB), jadi
    unduhan lewat urllib.read() bisa menggantung. ffmpeg men-decode sambil
    men-transcode ke mp3 48 kHz mono (kecil dan langsung siap dipakai).
    """
    if out_path.exists() and out_path.stat().st_size > 5000:
        return True
    url = f"https://xeno-canto.org/{xc_id}/download"
    for _ in range(max_attempts):
        try:
            subprocess.run(
                ["ffmpeg", "-y", "-loglevel", "error", "-i", url,
                 "-ar", "48000", "-ac", "1", "-b:a", "96k", str(out_path)],
                check=True, timeout=180, capture_output=True)
            if out_path.exists() and out_path.stat().st_size > 5000:
                return True
        except Exception:
            pass
        if out_path.exists():
            out_path.unlink(missing_ok=True)
        time.sleep(2.0)
    return False


def main() -> int:
    print("=== Unduh Negatif Non-Burung (Orthoptera + Kelelawar) ===")
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # Kumpulkan rekaman kandidat
    kandidat = {}  # sci -> (common, [recs])
    for grup in GRUP:
        for negara in NEGARA:
            for page in range(1, 6):
                data = cari(grup, negara, page)
                if not data:
                    # 400 = halaman di luar jangkauan (hasil sedikit); berhenti.
                    break
                recs = data.get("recordings", [])
                if not recs:
                    break
                for r in recs:
                    en = (r.get("en") or "").strip()
                    sci = f"{r.get('gen','')} {r.get('sp','')}".strip()
                    if not sci or not en:
                        continue
                    if r.get("q", "") not in ("A", "B", "C"):
                        continue
                    if not lisensi_aman(r.get("lic", "")):
                        continue
                    kandidat.setdefault(sci, (en, []))[1].append(r)

    print(f"Spesies kandidat non-burung: {len(kandidat)}")

    n_klip = 0
    n_sp = 0
    manifest = []
    for sci, (en, recs) in sorted(kandidat.items()):
        if n_klip >= MAKS_KLIP:
            break
        free = int(os.popen("df --output=avail . | tail -1").read().strip()) * 1024
        if free < 6 * 1024**3:
            print("DISK < 6 GB. Berhenti.")
            break

        d = AUDIO_DIR / sci.replace(" ", "_")
        d.mkdir(parents=True, exist_ok=True)
        sukses = 0
        perekam = {}
        for r in recs:
            if sukses >= 8 or n_klip + sukses >= MAKS_KLIP:
                break
            author = (r.get("rec") or "").strip().lower()
            if perekam.get(author, 0) >= 3:
                continue
            xc_id = int(r["id"])
            p = d / f"xc-{xc_id}.mp3"
            if unduh(xc_id, p):
                perekam[author] = perekam.get(author, 0) + 1
                sukses += 1
                manifest.append({
                    "clip_id": f"xc-{xc_id}",
                    "source": "xeno-canto",
                    "source_url": f"https://xeno-canto.org/{xc_id}",
                    "species_scientific": sci.replace(" ", "_"),
                    "species_common": en,
                    "quality": r.get("q", ""),
                    "license": r.get("lic", ""),
                    "author": r.get("rec", ""),
                    "country": r.get("cnt", ""),
                    "local_path": f"negatif_xc_nonburung/{sci.replace(' ', '_')}/xc-{xc_id}.mp3",
                })
            time.sleep(0.8)

        if sukses >= 1:
            n_sp += 1
            n_klip += sukses
            print(f"  [{n_sp}] {en} ({sci}): {sukses} klip (total {n_klip})")

    with open(MANIFEST_OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[
            "clip_id", "source", "source_url", "species_scientific",
            "species_common", "quality", "license", "author", "country",
            "local_path"])
        w.writeheader()
        w.writerows(manifest)

    print(f"\nSelesai: {n_sp} spesies, {n_klip} klip (target maks {MAKS_KLIP})")
    print(f"Manifest: {MANIFEST_OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())