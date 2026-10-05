"""Ambil metadata perekam dari XC API v3 — versi cepat dengan incremental save.

Fetch satu per satu via /api/3/recording/{id}, simpan setiap 50 ID.
Seed dari CSV yang sudah punya kolom author (field + uji_independen).
"""
import csv
import json
import os
import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent.parent
ML_DIR = ROOT / "ml"
DATA_DIR = ML_DIR / "data"
OUTPUT = DATA_DIR / "xc_meta.json"
API_SINGLE = "https://xeno-canto.org/api/3/recording"


def collect_ids():
    """Semua XC ID dari manifest + splits."""
    ids = set()
    for p in [
        DATA_DIR / "manifest_v2.csv",
        DATA_DIR / "manifest-clean.csv",
        DATA_DIR / "manifest.csv",
        DATA_DIR / "field" / "manifest.csv",
        DATA_DIR / "uji_independen" / "manifest.csv",
    ]:
        if not p.exists():
            continue
        with open(p, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                cid = row.get("clip_id", "").strip()
                if cid.startswith("xc-"):
                    ids.add(cid)
    # splits
    sp = DATA_DIR / "splits_v3.json"
    if sp.exists():
        for k in ("train", "val", "test"):
            for cid in json.loads(sp.read_text()).get(k, []):
                if cid.startswith("xc-"):
                    ids.add(cid)
    return sorted(ids)


def seed_from_csv():
    """Ambil metadata dari CSV field + uji_independen (sudah punya kolom author)."""
    cache = {}
    for p in [DATA_DIR / "field" / "manifest.csv", DATA_DIR / "uji_independen" / "manifest.csv"]:
        if not p.exists():
            continue
        with open(p, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                cid = row.get("clip_id", "").strip()
                author = row.get("author", "").strip()
                if not cid.startswith("xc-") or not author:
                    continue
                try:
                    lat = float(row["lat"]) if row.get("lat") else None
                except (ValueError, TypeError):
                    lat = None
                try:
                    lng = float(row.get("lng", row.get("lon", ""))) if row.get("lng", row.get("lon", "")) else None
                except (ValueError, TypeError):
                    lng = None
                cache[cid] = {
                    "rec": author,
                    "loc": row.get("country", ""),
                    "lat": lat,
                    "lng": lng,
                    "date": row.get("recorded_on", row.get("date", "")),
                    "cnt": row.get("country", ""),
                    "sp": row.get("species_scientific", ""),
                }
    return cache


def fetch_one(xc_num, api_key):
    url = f"{API_SINGLE}/{xc_num}?key={api_key}"
    req = Request(url, headers={"User-Agent": "GemaHutan/1.0"})
    try:
        with urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


def save_cache(cache, xc_ids):
    groups = {}
    for cid in xc_ids:
        m = cache.get(cid, {})
        if m.get("rec") and m.get("lat") is not None:
            groups[cid] = f"{m['rec']}_{round(m['lat'], 2)}_{round(m.get('lng', 0), 2)}"
        else:
            try:
                num = int(cid.replace("xc-", ""))
                groups[cid] = f"xc_chain_{num // 10}"
            except ValueError:
                groups[cid] = f"unknown_{cid}"
    with_rec = sum(1 for c in xc_ids if c in cache and cache[c].get("rec"))
    OUTPUT.write_text(json.dumps({
        "recordings": cache,
        "xc_ids": xc_ids,
        "groups": groups,
        "coverage_rec_pct": round(with_rec / len(xc_ids) * 100, 1) if xc_ids else 0,
        "n_total": len(xc_ids),
        "n_with_rec": with_rec,
        "n_groups": len(set(groups.values())),
    }, indent=2, ensure_ascii=False))


def main():
    api_key = os.environ.get("XC_API_KEY")
    if not api_key:
        env = ROOT / ".env"
        if env.exists():
            for line in env.read_text().splitlines():
                if line.startswith("XC_API_KEY="):
                    api_key = line.split("=", 1)[1].strip()
    if not api_key:
        print("ERROR: XC_API_KEY not set")
        return 1

    print("Collecting IDs...")
    xc_ids = collect_ids()
    print(f"Total: {len(xc_ids)} unique XC IDs")

    # Seed dari CSV
    cache = seed_from_csv()
    print(f"Seeded {len(cache)} from CSV (field + uji_independen)")

    # Load existing cache
    if OUTPUT.exists():
        existing = json.loads(OUTPUT.read_text()).get("recordings", {})
        for cid, val in existing.items():
            if cid not in cache:
                cache[cid] = val
        print(f"Loaded {len(existing)} from existing cache, merged {len(cache)} total")

    missing = [c for c in xc_ids if c not in cache or not cache[c].get("rec")]
    print(f"Need fetch: {len(missing)} IDs")

    if not missing:
        print("All done!")
        save_cache(cache, xc_ids)
        return 0

    t0 = time.time()
    success = 0
    for i, cid in enumerate(missing):
        xc_num = cid.replace("xc-", "")
        rec = fetch_one(xc_num, api_key)
        if rec and "id" in rec:
            cache[cid] = {
                "rec": rec.get("rec", ""),
                "loc": rec.get("loc", ""),
                "lat": float(rec["lat"]) if rec.get("lat") else None,
                "lng": float(rec["lon"]) if rec.get("lon") else None,
                "date": rec.get("date", ""),
                "cnt": rec.get("cnt", ""),
                "sp": f"{rec.get('gen', '')} {rec.get('sp', '')}".strip(),
            }
            success += 1

        if (i + 1) % 50 == 0 or i == len(missing) - 1:
            elapsed = time.time() - t0
            eta = (elapsed / (i + 1)) * (len(missing) - i - 1) if i < len(missing) - 1 else 0
            print(f"  {i + 1}/{len(missing)} ({success} ok, {elapsed:.0f}s, ETA {eta:.0f}s)")
            save_cache(cache, xc_ids)

        if i < len(missing) - 1:
            time.sleep(0.25)

    elapsed = time.time() - t0
    with_rec = sum(1 for c in xc_ids if c in cache and cache[c].get("rec"))
    cov = with_rec / len(xc_ids) * 100
    print(f"\nDone in {elapsed:.0f}s: {with_rec}/{len(xc_ids)} have rec ({cov:.1f}%)")

    if cov < 95:
        print("WARNING: below 95% target")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())