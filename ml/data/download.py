"""Download bird audio from Xeno-canto API v3. Idempotent and resumable."""
import argparse
import csv
import hashlib
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).parent
AUDIO_DIR = BASE_DIR / "audio"
MANIFEST = BASE_DIR / "manifest.csv"
SPECIES_FILE = BASE_DIR / "species_list.json"

XC_API = "https://xeno-canto.org/api/3/recordings"
XC_API_KEY = os.getenv("XC_API_KEY", "")
RATE_LIMIT = 0.5  # seconds between requests


def load_species_list():
    with open(SPECIES_FILE) as f:
        return json.load(f)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch_xc(query, page=1, per_page=50):
    """Query Xeno-canto API v3 with retry. Uses tag-based queries."""
    params = {
        "query": query,
        "page": page,
        "per_page": per_page,
    }
    if XC_API_KEY:
        params["key"] = XC_API_KEY

    url = f"{XC_API}?{urllib.parse.urlencode(params)}"
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "GemaHutan/0.1 (research)"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode())
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            wait = min(2 ** attempt + 1, 60)
            print(f"  Retry {attempt+1}/5 after {wait}s: {e}")
            time.sleep(wait)
    return None


def download_file(url, dest, max_retries=3):
    """Download with retry."""
    for attempt in range(max_retries):
        try:
            if url.startswith("//"):
                url = "https:" + url
            req = urllib.request.Request(url, headers={"User-Agent": "GemaHutan/0.1 (research)"})
            if XC_API_KEY:
                req.add_header("key", XC_API_KEY)
            with urllib.request.urlopen(req, timeout=120) as resp:
                with open(dest, "wb") as f:
                    while True:
                        chunk = resp.read(8192)
                        if not chunk:
                            break
                        f.write(chunk)
            return True
        except Exception as e:
            wait = min(2 ** attempt + 1, 30)
            print(f"  Download retry {attempt+1}/{max_retries}: {e}")
            time.sleep(wait)
    return False


def load_existing_manifest():
    """Load already-downloaded clip IDs."""
    existing = {}
    if MANIFEST.exists():
        with open(MANIFEST) as f:
            reader = csv.DictReader(f)
            for row in reader:
                existing[row["clip_id"]] = row
    return existing


def download_species(species, existing, max_clips=60):
    """Download clips for one species from Xeno-canto v3."""
    sci_name = species["scientific_name"]
    # v3 uses tag-based queries: sp:"genus species"
    # Try Indonesia first, then global
    queries = [
        f'sp:"{sci_name}" cnt:Indonesia q:A',
        f'sp:"{sci_name}" cnt:Indonesia',
        f'sp:"{sci_name}" q:A',
        f'sp:"{sci_name}"',
    ]

    clips = []
    seen_ids = set()
    
    for query in queries:
        if len(clips) >= max_clips:
            break
        
        page = 1
        while len(clips) < max_clips:
            data = fetch_xc(query, page=page)
            if not data or "recordings" not in data:
                break

            recordings = data["recordings"]
            if not recordings:
                break

            for rec in recordings:
                if len(clips) >= max_clips:
                    break

                rec_id = rec["id"]
                if rec_id in seen_ids:
                    continue
                seen_ids.add(rec_id)

                clip_id = f"xc-{rec_id}"

                # Skip if already downloaded
                if clip_id in existing:
                    clips.append(existing[clip_id])
                    continue

                # Skip restricted (no download link)
                file_url = rec.get("file")
                if not file_url:
                    continue

                # Download audio
                local_name = f"{clip_id}.mp3"
                local_path = AUDIO_DIR / sci_name.replace(" ", "_") / local_name
                local_path.parent.mkdir(parents=True, exist_ok=True)

                if local_path.exists() and local_path.stat().st_size > 1000:
                    sha = sha256_file(local_path)
                else:
                    print(f"  Downloading {clip_id}: {rec.get('en', sci_name)}")
                    ok = download_file(file_url, str(local_path))
                    if not ok:
                        continue
                    if not local_path.exists() or local_path.stat().st_size < 500:
                        print(f"  Skipping {clip_id}: too small or missing")
                        continue
                    sha = sha256_file(local_path)
                    time.sleep(RATE_LIMIT)

                clip = {
                    "clip_id": clip_id,
                    "source": "xeno-canto",
                    "source_url": f"https://xeno-canto.org/{rec_id}",
                    "species_scientific": sci_name,
                    "species_common": rec.get("en", ""),
                    "split": "",  # assigned later by split script
                    "duration_s": rec.get("length", "0:00"),
                    "sample_rate": rec.get("smp", ""),
                    "quality": rec.get("q", ""),
                    "license": rec.get("lic", ""),
                    "sha256": sha,
                    "local_path": str(local_path.relative_to(BASE_DIR)),
                }
                clips.append(clip)
                existing[clip_id] = clip

            num_pages = int(data.get("numPages", 1))
            if page >= num_pages:
                break
            page += 1
            time.sleep(RATE_LIMIT)

    return clips


def download_negatives(existing, max_clips=300):
    """Download negative samples: rain, wind, insects, traffic, silence."""
    neg_queries = [
        ('rain', 'type:rain grp:soundscape'),
        ('wind', 'type:wind grp:soundscape'),
        ('insects', 'grp:grasshoppers'),
        ('frogs', 'grp:frogs cnt:Indonesia'),
    ]
    
    clips = []
    per_category = max_clips // len(neg_queries)
    
    for label, query in neg_queries:
        cat_clips = 0
        page = 1
        while cat_clips < per_category:
            data = fetch_xc(query, page=page, per_page=50)
            if not data or not data.get("recordings"):
                break
            
            for rec in data["recordings"]:
                if cat_clips >= per_category:
                    break
                
                clip_id = f"xc-neg-{rec['id']}"
                if clip_id in existing:
                    clips.append(existing[clip_id])
                    cat_clips += 1
                    continue
                
                file_url = rec.get("file")
                if not file_url:
                    continue
                
                local_name = f"{clip_id}.mp3"
                local_path = AUDIO_DIR / "_negative" / local_name
                local_path.parent.mkdir(parents=True, exist_ok=True)
                
                if local_path.exists() and local_path.stat().st_size > 1000:
                    sha = sha256_file(local_path)
                else:
                    print(f"  Downloading negative {clip_id} ({label})")
                    ok = download_file(file_url, str(local_path))
                    if not ok:
                        continue
                    sha = sha256_file(local_path)
                    time.sleep(RATE_LIMIT)
                
                clip = {
                    "clip_id": clip_id,
                    "source": "xeno-canto",
                    "source_url": f"https://xeno-canto.org/{rec['id']}",
                    "species_scientific": "_negative",
                    "species_common": f"negative_{label}",
                    "split": "",
                    "duration_s": rec.get("length", "0:00"),
                    "sample_rate": rec.get("smp", ""),
                    "quality": rec.get("q", ""),
                    "license": rec.get("lic", ""),
                    "sha256": sha,
                    "local_path": str(local_path.relative_to(BASE_DIR)),
                }
                clips.append(clip)
                existing[clip_id] = clip
                cat_clips += 1
            
            num_pages = int(data.get("numPages", 1))
            if page >= num_pages:
                break
            page += 1
            time.sleep(RATE_LIMIT)
        
        print(f"  Negatives ({label}): {cat_clips} clips")
    
    return clips


def _write_manifest(clips):
    fieldnames = [
        "clip_id", "source", "source_url", "species_scientific", "species_common",
        "split", "duration_s", "sample_rate", "quality", "license", "sha256", "local_path",
    ]
    with open(MANIFEST, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for c in clips:
            row = {k: c.get(k, "") for k in fieldnames}
            writer.writerow(row)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="Limit species count")
    parser.add_argument("--clips-per-species", type=int, default=60)
    parser.add_argument("--negatives", type=int, default=300)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-negatives", action="store_true")
    args = parser.parse_args()

    if not XC_API_KEY:
        print("WARNING: XC_API_KEY not set. Set it in .env or environment.")
        print("  export XC_API_KEY=your-key-here")

    AUDIO_DIR.mkdir(parents=True, exist_ok=True)

    species_list = load_species_list()
    if args.limit:
        species_list = species_list[:args.limit]

    print(f"Target: {len(species_list)} species, {args.clips_per_species} clips each")

    if args.dry_run:
        for sp in species_list:
            print(f"  Would download: {sp['scientific_name']}")
        return

    existing = load_existing_manifest()
    # Keep only real XC clips (not synthetic)
    real_clips = {k: v for k, v in existing.items() if k.startswith("xc-")}
    all_clips = list(real_clips.values())

    for i, sp in enumerate(species_list):
        print(f"[{i+1}/{len(species_list)}] {sp['scientific_name']}")
        clips = download_species(sp, real_clips, max_clips=args.clips_per_species)
        print(f"  Got {len(clips)} clips")

        for c in clips:
            if c["clip_id"] not in {x["clip_id"] for x in all_clips}:
                all_clips.append(c)

        # Write manifest after each species (resumable)
        _write_manifest(all_clips)

    if not args.skip_negatives:
        print(f"\nDownloading {args.negatives} negative samples...")
        neg_clips = download_negatives(real_clips, max_clips=args.negatives)
        for c in neg_clips:
            if c["clip_id"] not in {x["clip_id"] for x in all_clips}:
                all_clips.append(c)
        _write_manifest(all_clips)

    # Summary
    from collections import Counter
    species_counts = Counter(c["species_scientific"] for c in all_clips)
    print("\n=== SUMMARY ===")
    print(f"Total clips: {len(all_clips)}")
    print(f"Species: {len(species_counts)}")
    for sp, count in species_counts.most_common():
        print(f"  {sp}: {count}")


if __name__ == "__main__":
    main()
