"""Generate 8 tingkat degradasi penuh dari splits test ND-free, multiprocessing.

Berlari paralel dengan ProcessPoolExecutor. Tiap file independen, jadi tidak
ada shared state yang rentan race condition. Output deterministic per clip
karena ffmpeg deterministik dan input file sama.

Pakai:
    cd ~/Projects/gemahutan
    source .venv/bin/activate
    OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 python3 ml/degrade_full.py
"""
from __future__ import annotations

import argparse
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "2")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "2")
os.environ.setdefault("MKL_NUM_THREADS", "2")
os.environ.setdefault("PYTHONHASHSEED", "0")

import sys

ML = Path(__file__).resolve().parent
sys.path.insert(0, str(ML.parent))

import degradation as dg  # noqa: E402


def worker(args):
    """Generate satu clip pada satu tier. Return (tier, clip_id, ok, msg)."""
    rec, tier_name, tier, batas = args
    sumber = dg.DATA_DIR / rec["local_path"]
    if not sumber.exists():
        return (tier_name, rec["clip_id"], False, "missing audio")
    tujuan = dg.OUT_DIR / tier_name / f"{rec['clip_id']}.wav"
    if tujuan.exists():
        return (tier_name, rec["clip_id"], True, "cached")
    rms = dg.rms_berkas(sumber)
    cmd = dg.bangun_perintah(sumber, tujuan, tier, rms, batas_detik=batas)
    import subprocess
    hasil = subprocess.run(cmd, capture_output=True, text=True)
    ok = hasil.returncode == 0 and tujuan.exists()
    msg = "" if ok else hasil.stderr.strip()[:80]
    return (tier_name, rec["clip_id"], ok, msg)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--workers", type=int, default=8)
    p.add_argument("--batas-detik", type=float, default=3.0)
    p.add_argument("--sampel", type=int, default=None,
                   help="acak dan ambil N klip dari test (default semua)")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--sampel-tiers", type=str, default=None,
                   help="mis. 'kontrol_reencode,hujan_ringan' untuk subset")
    args = p.parse_args()

    # Reset OUT_DIR ke degraded (sebelumnya subset ada di sini, sudah dihapus).
    dg.OUT_DIR = ML / "data" / "degraded"
    dg.PARAMS = dg.OUT_DIR / "params.json"
    dg.OUT_DIR.mkdir(parents=True, exist_ok=True)

    tiers_pilihan = (
        [t.strip() for t in args.sampel_tiers.split(",") if t.strip() in dg.TIERS]
        if args.sampel_tiers
        else list(dg.TIERS.keys())
    )

    klip = dg.klip_uji()
    if args.sampel and args.sampel < len(klip):
        import random
        rnd = random.Random(args.seed)
        klip = rnd.sample(klip, args.sampel)

    print(f"klip: {len(klip)} | tiers: {tiers_pilihan} | workers: {args.workers}"
          f" | batas_detik: {args.batas_detik}s")

    jobs = []
    for tier_name in tiers_pilihan:
        (dg.OUT_DIR / tier_name).mkdir(parents=True, exist_ok=True)
        for rec in klip:
            jobs.append((rec, tier_name, dg.TIERS[tier_name], args.batas_detik))

    sukses = 0
    gagal = 0
    gagal_log = []
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        future_to_job = {ex.submit(worker, j): j for j in jobs}
        for i, fut in enumerate(as_completed(future_to_job), 1):
            tier, cid, ok, msg = fut.result()
            if ok:
                sukses += 1
            else:
                gagal += 1
                gagal_log.append((tier, cid, msg))
            if i % 100 == 0 or i == len(jobs):
                pct = i / len(jobs) * 100
                print(f"  [{pct:5.1f}%] {i}/{len(jobs)} (sukses={sukses}, gagal={gagal})")

    print(f"\nSelesai: {sukses}/{len(jobs)} sukses, {gagal} gagal")
    if gagal:
        print("Sample kegagalan:")
        for t, c, m in gagal_log[:10]:
            print(f"  {t}/{c}: {m}")

    import json
    dg.PARAMS.write_text(json.dumps({
        "catatan": "Simulasi degradasi, bukan rekaman lapangan",
        "desain": "derau disetel terhadap SNR terukur dari tiap klip",
        "sample_rate": 48000,
        "channels": 1,
        "faktor_derau_amplitudo_1": dict(dg._FAKTOR_DERAU),
        "sumber_klip": "ml/data/splits.json bagian test (ND-free, n=127)",
        "tingkat": dg.TIERS,
        "jumlah_berkas": sukses,
        "workers": args.workers,
        "batas_detik": args.batas_detik,
    }, indent=2, ensure_ascii=False))
    print(f"Parameter di {dg.PARAMS.relative_to(ML.parent)}")


if __name__ == "__main__":
    main()
