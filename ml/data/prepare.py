"""Create train/val/test splits. Split by clip (no recording leakage).
70/15/15 stratified per species."""
import csv
import json
import random
from collections import defaultdict
from pathlib import Path

BASE_DIR = Path(__file__).parent
MANIFEST = BASE_DIR / "manifest.csv"
SPLITS_FILE = BASE_DIR / "splits.json"


def main():
    random.seed(42)

    # Load manifest
    with open(MANIFEST) as f:
        reader = csv.DictReader(f)
        clips = list(reader)

    # Group by species
    by_species = defaultdict(list)
    for clip in clips:
        by_species[clip["species_scientific"]].append(clip["clip_id"])

    splits = {"train": [], "val": [], "test": []}
    stats = {}

    for species, clip_ids in sorted(by_species.items()):
        random.shuffle(clip_ids)
        n = len(clip_ids)
        n_test = max(1, int(n * 0.15))
        n_val = max(1, int(n * 0.15))
        n_train = n - n_test - n_val

        splits["test"].extend(clip_ids[:n_test])
        splits["val"].extend(clip_ids[n_test:n_test + n_val])
        splits["train"].extend(clip_ids[n_test + n_val:])

        stats[species] = {"train": n_train, "val": n_val, "test": n_test, "total": n}

    # Update manifest with split info
    clip_to_split = {}
    for split_name, ids in splits.items():
        for cid in ids:
            clip_to_split[cid] = split_name

    updated = []
    with open(MANIFEST) as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            row["split"] = clip_to_split.get(row["clip_id"], "")
            updated.append(row)

    with open(MANIFEST, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(updated)

    # Save splits
    output = {
        "train": splits["train"],
        "val": splits["val"],
        "test": splits["test"],
        "stats": stats,
    }
    with open(SPLITS_FILE, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Splits: train={len(splits['train'])}, val={len(splits['val'])}, test={len(splits['test'])}")
    print(f"Species: {len(stats)}")
    print(f"Saved to {SPLITS_FILE}")


if __name__ == "__main__":
    main()
