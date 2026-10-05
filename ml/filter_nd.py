"""Filter ND-licensed clips from manifest, regenerate splits.

ND = NoDerivatives; we drop them to keep dataset license-clean.
Standard: setiap 25 spesies + _negative masih punya >=5 klip.
"""

import csv
import json
from collections import defaultdict
from pathlib import Path

BASE = Path(__file__).parent / "data"
MANIFEST = BASE / "manifest.csv"
SPLITS = BASE / "splits.json"
OUT_MANIFEST = BASE / "manifest-clean.csv"
OUT_SPLITS = BASE / "splits-clean.json"


def is_nd(license_str: str) -> bool:
    return "nd" in (license_str or "").lower()


def main():
    with open(MANIFEST) as f:
        rows = list(csv.DictReader(f))

    before_total = len(rows)
    keep = [r for r in rows if not is_nd(r.get("license", ""))]
    dropped = before_total - len(keep)

    # Per-species counts after filter (use species_scientific + _negative)
    per_species = defaultdict(int)
    for r in keep:
        per_species[r["species_scientific"]] += 1

    # Recompute splits from kept clip_ids.
    # Use seed 42 stratified 70/15/15 (prepare.py's logic). Same algorithm.
    import random
    random.seed(42)

    by_species = defaultdict(list)
    for r in keep:
        by_species[r["species_scientific"]].append(r["clip_id"])

    splits = {"train": [], "val": [], "test": []}
    stats = {}
    for species, ids in sorted(by_species.items()):
        random.shuffle(ids)
        n = len(ids)
        n_test = max(1, int(n * 0.15))
        n_val = max(1, int(n * 0.15))
        n_train = n - n_test - n_val
        splits["test"].extend(ids[:n_test])
        splits["val"].extend(ids[n_test:n_test + n_val])
        splits["train"].extend(ids[n_test + n_val:])
        stats[species] = {"train": n_train, "val": n_val, "test": n_test, "total": n}

    # Update manifest with split info so downstream loads stay consistent.
    clip_split = {}
    for name, ids in splits.items():
        for cid in ids:
            clip_split[cid] = name

    with open(OUT_MANIFEST, "w", newline="") as f:
        fieldnames = list(rows[0].keys())
        # Ensure 'split' field name matches source
        if "split" not in fieldnames:
            fieldnames.insert(5, "split")  # right after species_common
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in keep:
            r["split"] = clip_split.get(r["clip_id"], "")
            writer.writerow(r)

    with open(OUT_SPLITS, "w") as f:
        json.dump({"splits": splits, "stats": stats, "total_clips": len(keep)}, f, indent=2)

    print(f"Before: {before_total}")
    print(f"Dropped ND: {dropped}")
    print(f"After: {len(keep)}")
    print(f"Splits: train={len(splits['train'])}, val={len(splits['val'])}, test={len(splits['test'])}")
    print()

    # Per-species log
    expected_species = [
        "Passer montanus", "Cinnyris jugularis", "Pycnonotus aurigaster",
        "Pycnonotus goiavier", "Aegithina tiphia", "Orthotomus sutorius",
        "Arachnothera longirostra", "Anthreptes malacensis", "Spilopelia chinensis",
        "Geopelia striata", "Corvus macrorhynchos", "Gallus gallus",
        "Amaurornis phoenicurus", "Dicrurus macrocercus", "Todiramphus chloris",
        "Lonchura punctulata", "Rhipidura javanica", "Chalcophaps indica",
        "Merops philippinus", "Centropus bengalensis", "Aplonis panayensis",
        "Cisticola juncidis", "Haliastur indus", "Hirundo tahitica",
        "Prinia familiaris",
    ]
    print(f"{'Species':<32} {'Count':>6}  >=5?")
    print("-" * 50)
    bad = []
    for sp in expected_species:
        c = per_species.get(sp, 0)
        ok = "OK" if c >= 5 else "FAIL"
        if c < 5:
            bad.append((sp, c))
        print(f"{sp:<32} {c:>6}  {ok}")
    # _negative class
    neg_count = sum(1 for r in keep if r["species_scientific"] == "_negative")
    neg_ok = "OK" if neg_count >= 5 else "FAIL"
    print(f"{'_negative':<32} {neg_count:>6}  {neg_ok}")
    print()

    # Species not in expected list
    extras = sorted(set(per_species.keys()) - set(expected_species) - {"_negative"})
    if extras:
        print(f"Extra species in manifest: {extras}")
        for sp in extras:
            print(f"  {sp}: {per_species[sp]}")

    if bad:
        print(f"\nFAIL: {len(bad)} spesies di bawah 5 klip.")
        return 1
    print(f"\nAll {len(expected_species)} spesies + _negative >= 5 klip.")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
