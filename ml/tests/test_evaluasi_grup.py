"""Test: evaluasi_grup.get_groups tidak ada XC clip yang jatuh ke fallback.

Jalankan: pytest ml/tests/test_evaluasi_grup.py -q
"""

import json
import sys
from pathlib import Path

import pytest

ML_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ML_DIR.parent))

from ml.evaluasi_grup import get_groups  # noqa: E402


def test_semua_xc_punya_grup_dari_recordings():
    """Semua klip XC di manifest harus punya grup dari recordings, bukan fallback."""
    meta_file = ML_DIR / "data" / "xc_meta.json"
    if not meta_file.exists():
        pytest.skip("xc_meta.json tidak ada")

    meta = json.loads(meta_file.read_text())
    assert meta.get("recordings"), "xc_meta.json tidak punya recordings"
    # Kumpulkan semua XC clip_id dari manifest
    manifest = ML_DIR / "data" / "manifest.csv"
    if not manifest.exists():
        pytest.skip("manifest.csv tidak ada")

    xc_ids = set()
    with open(manifest) as f:
        for line in f.readlines()[1:]:
            cid = line.strip().split(",")[0].strip()
            if cid.startswith("xc-"):
                xc_ids.add(cid)

    groups = get_groups(list(xc_ids))

    fallback = []
    for cid in sorted(xc_ids):
        grp = groups.get(cid, "")
        if grp.startswith("xc_chain_"):
            fallback.append(cid)

    assert not fallback, (
        f"{len(fallback)} klip XC jatuh ke fallback rantai: "
        f"{fallback[:10]}{'...' if len(fallback) > 10 else ''}"
    )


def test_grup_tidak_kosong():
    """Semua grup harus non-empty string."""
    xc_ids = ["xc-1082290", "xc-1059451", "xc-661284"]  # known IDs
    groups = get_groups(xc_ids)
    for cid in xc_ids:
        assert groups.get(cid), f"{cid} punya grup kosong"
        assert not groups[cid].startswith("xc_chain_"), (
            f"{cid} jatuh ke fallback: {groups[cid]}"
        )