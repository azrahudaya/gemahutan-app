"""Evaluasi end-to-end: CascadeEngine.predict pada korpus lapangan dan uji independen.

Jalur produksi (CascadeEngine, termasuk penyaring). Cache per berkas di
ml/data/cache_e2e/ (gitignored).

Setiap berkas punya kunci `bagian` (pilih/lapor) dari pembagian_openset.json.
Semua ekstensi audio didukung. Berkas yang gagal didekode masuk daftar `gagal`.

Output: ml/reports/e2e.json (skema C11) + e2e.md

Jalankan: python3 ml/evaluasi_e2e.py
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

ML_DIR = ROOT / "ml"
FIELD_AUDIO = ML_DIR / "data" / "field" / "audio"
INDEP_AUDIO = ML_DIR / "data" / "uji_independen" / "audio"
INDEP_MANIFEST = ML_DIR / "data" / "uji_independen" / "manifest.csv"
FIELD_MANIFEST = ML_DIR / "data" / "field" / "manifest.csv"
CHECKPOINT = ML_DIR / "checkpoints"
MANIFEST = CHECKPOINT / "MANIFEST.json"
PEMBAGIAN = ML_DIR / "data" / "pembagian_openset.json"
CACHE_E2E = ML_DIR / "data" / "cache_e2e"
REPORTS = ML_DIR / "reports"

AUDIO_EXT = {".wav", ".mp3", ".m4a", ".ogg", ".flac", ".opus", ".webm", ".aac"}
# Ekstensi yang butuh konversi ffmpeg ke wav (soundfile/birdnetlib tak bisa baca)
BUTUH_KONVERSI = {".m4a", ".ogg", ".opus", ".webm", ".aac", ".flac"}


def konversi_ke_wav(path: Path, wav_dir: Path) -> Path | None:
    """Konversi audio ke wav sementara via ffmpeg. Return path wav atau None."""
    import subprocess

    wav_path = wav_dir / f"{path.stem}.wav"
    if wav_path.exists():
        return wav_path
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", str(path),
             "-ar", "48000", "-ac", "1", str(wav_path)],
            check=True, timeout=120, capture_output=True)
        return wav_path
    except Exception:
        return None


def muat_cascade():
    from ml.engines.cascade import CascadeEngine
    engine = CascadeEngine()
    engine._ensure_loaded()
    return engine


def species_dari_folder(folder_name: str) -> str:
    return folder_name.replace('_', ' ')


def muat_pembagian() -> dict:
    return json.loads(PEMBAGIAN.read_text())


def tentukan_bagian(local_path: str, pembagian: dict, korpus: str) -> str:
    """Tentukan pilih/lapor untuk berkas field, uji_independen selalu lapor."""
    if korpus == "uji_independen":
        return "lapor"
    # Normalisasi path
    norm = local_path.replace("ml/data/", "").replace("data/", "")
    if norm in pembagian.get("berkas_target_pilih", []):
        return "pilih"
    if norm in pembagian.get("berkas_target_lapor", []):
        return "lapor"
    # Pengecoh: tentukan dari spesies folder
    for sp in pembagian.get("spesies_pengecoh_pilih", []):
        if f"/{sp}/" in norm:
            return "pilih"
    for sp in pembagian.get("spesies_pengecoh_lapor", []):
        if f"/{sp}/" in norm:
            return "lapor"
    # Fallback: lapor (aman, tidak dipakai memilih)
    return "lapor"


def daftar_berkas_field(pembagian: dict):
    out = []
    for korpus in ["inat", "xc_noisy", "other"]:
        base = FIELD_AUDIO / korpus
        if not base.exists():
            continue
        for sub in sorted(base.iterdir()):
            if not sub.is_dir():
                continue
            sp = species_dari_folder(sub.name)
            for f in sorted(sub.rglob("*")):
                if f.is_dir():
                    continue
                if f.suffix.lower() not in AUDIO_EXT:
                    continue
                local_path = f"ml/data/{f.relative_to(ML_DIR / 'data')}"
                bagian = tentukan_bagian(local_path, pembagian, f"field/{korpus}")
                if korpus == "other":
                    out.append((f, f"field/{korpus}", [], bagian))
                else:
                    out.append((f, f"field/{korpus}", [sp], bagian))
    return out


def daftar_berkas_independen():
    man = {}
    with open(INDEP_MANIFEST, newline='') as f:
        for row in csv.DictReader(f):
            man[row["clip_id"]] = row["species_scientific"]

    out = []
    for p in sorted(INDEP_AUDIO.rglob("*")):
        if p.suffix.lower() not in AUDIO_EXT:
            continue
        cid = p.stem
        sp = man.get(cid)
        if sp is None:
            continue
        out.append((p, "uji_independen", [sp], "lapor"))
    return out


def durasi_audio(path: Path) -> float:
    try:
        import soundfile as sf
        info = sf.info(str(path))
        return float(info.frames / info.samplerate)
    except Exception:
        return 0.0


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--out-json", default=str(REPORTS / "e2e.json"),
                    help="lokasi output JSON")
    ap.add_argument("--cache-dir", default=str(CACHE_E2E),
                    help="direktori cache deteksi final")
    args = ap.parse_args()

    out_json = Path(args.out_json)
    cache_dir = Path(args.cache_dir)

    print("Memuat CascadeEngine (jalur produksi)...")
    engine = muat_cascade()
    target_set = set(engine._indonesian_species)

    ckpt_dir = Path(os.getenv("GEMAHUTAN_CHECKPOINT_DIR", str(CHECKPOINT)))
    ckpt_file = ckpt_dir / "best_model.npz"
    if ckpt_file.exists():
        sha256_ckpt = hashlib.sha256(ckpt_file.read_bytes()).hexdigest()
    elif MANIFEST.exists():
        sha256_ckpt = json.loads(MANIFEST.read_text())["files"]["best_model.npz"]["sha256"]
    else:
        sha256_ckpt = ""
    pembagian = muat_pembagian()

    berkas = daftar_berkas_field(pembagian) + daftar_berkas_independen()
    print(f"Total berkas berlabel: {len(berkas)}")

    cache_dir.mkdir(parents=True, exist_ok=True)
    berkas_ids = [str(path.relative_to(ML_DIR / "data")) for path, *_ in berkas]
    pool_sha256 = hashlib.sha256("\n".join(sorted(berkas_ids)).encode("utf-8")).hexdigest()
    n_field = sum(1 for _, korpus, _, _ in berkas if korpus.startswith("field/"))
    n_indep = sum(1 for _, korpus, _, _ in berkas if korpus == "uji_independen")
    n_pilih = sum(1 for _, _, _, bagian in berkas if bagian == "pilih")
    n_lapor = sum(1 for _, _, _, bagian in berkas if bagian == "lapor")
    pool_info = {
        "n_total": len(berkas),
        "n_field": n_field,
        "n_uji_independen": n_indep,
        "n_pilih": n_pilih,
        "n_lapor": n_lapor,
        "sha256_daftar_berkas": pool_sha256,
    }
    print(f"Pool: total {n_field+n_indep} (field {n_field}, independen {n_indep}), pilih {n_pilih}, lapor {n_lapor}")
    print(f"Pool sha256: {pool_sha256}")

    cache_wav = cache_dir / "wav"
    cache_wav.mkdir(parents=True, exist_ok=True)


    per_berkas = []
    gagal = []
    t_start = time.time()

    for i, (path, korpus, benar, bagian) in enumerate(berkas):
        rel = path.relative_to(ML_DIR / "data")
        cache_file = cache_dir / f"{str(rel).replace('/', '__')}__.json"
        try:
            if cache_file.exists():
                detections = json.loads(cache_file.read_text())
            else:
                # Konversi kalau perlu
                proses_path = path
                if path.suffix.lower() in BUTUH_KONVERSI:
                    wav = konversi_ke_wav(path, cache_wav)
                    if wav is None:
                        gagal.append({"berkas": str(path.relative_to(ML_DIR / "data")),
                                      "alasan": "konversi ffmpeg gagal"})
                        continue
                    proses_path = wav
                hasil = engine.predict(str(proses_path))
                detections = [
                    {"species": d.species_scientific, "confidence": d.confidence,
                     "engine": d.engine}
                    for d in hasil
                ]
                cache_file.write_text(json.dumps(detections))
        except Exception as e:
            gagal.append({"berkas": str(path.relative_to(ML_DIR / "data")),
                          "alasan": str(e)[:200]})
            continue

        terdeteksi = sorted({d["species"] for d in detections if d["species"] in target_set})
        nontarget = sorted({d["species"] for d in detections if d["species"] not in target_set})

        per_berkas.append({
            "berkas": str(path.relative_to(ML_DIR / "data")),
            "korpus": korpus,
            "bagian": bagian,
            "durasi_s": round(durasi_audio(path), 2),
            "benar": benar,
            "terdeteksi": terdeteksi,
            "nontarget": nontarget,
        })

        if (i + 1) % 50 == 0:
            print(f"  {i + 1}/{len(berkas)}... ({time.time() - t_start:.0f}s)")

    # Agregat
    tp = fp = fn = 0.0
    for b in per_berkas:
        benar_set = set(b["benar"])
        deteksi_set = set(b["terdeteksi"])
        tp += len(benar_set & deteksi_set)
        fp += len(deteksi_set - benar_set)
        fn += len(benar_set - deteksi_set)
    presisi = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0

    # Per korpus
    per_korpus = {}
    for korpus_name in ["field/inat", "field/xc_noisy", "field/other", "uji_independen"]:
        subset = [b for b in per_berkas if b["korpus"] == korpus_name]
        if not subset:
            continue
        if korpus_name == "field/other":
            total_menit = sum(b["durasi_s"] for b in subset) / 60.0
            fp_count = sum(len(b["terdeteksi"]) for b in subset)
            per_korpus[korpus_name] = {
                "deteksi_palsu_per_menit": round(fp_count / total_menit, 4) if total_menit > 0 else 0.0,
                "berkas_dengan_deteksi_target": sum(1 for b in subset if b["terdeteksi"]),
                "n_berkas": len(subset),
            }
        else:
            k_tp = k_fp = k_fn = 0.0
            for b in subset:
                benar_set = set(b["benar"])
                deteksi_set = set(b["terdeteksi"])
                k_tp += len(benar_set & deteksi_set)
                k_fp += len(deteksi_set - benar_set)
                k_fn += len(benar_set - deteksi_set)
            per_korpus[korpus_name] = {
                "presisi": round(k_tp / (k_tp + k_fp), 4) if (k_tp + k_fp) > 0 else 0.0,
                "recall": round(k_tp / (k_tp + k_fn), 4) if (k_tp + k_fn) > 0 else 0.0,
                "n_berkas": len(subset),
            }

    # Per spesies
    per_spesies = {}
    for sp in sorted(target_set):
        subset = [b for b in per_berkas if sp in b["benar"]]
        if not subset:
            continue
        s_tp = sum(1 for b in subset if sp in b["terdeteksi"])
        s_fn = len(subset) - s_tp
        s_fp = sum(1 for b in per_berkas if sp in b["terdeteksi"] and sp not in b["benar"])
        per_spesies[sp] = {
            "presisi": round(s_tp / (s_tp + s_fp), 4) if (s_tp + s_fp) > 0 else 0.0,
            "recall": round(s_tp / (s_tp + s_fn), 4) if (s_tp + s_fn) > 0 else 0.0,
            "n_berkas": len(subset),
        }

    nontarget_counts = [len(b["nontarget"]) for b in per_berkas]
    spesies_nontarget_per_berkas = float(np.mean(nontarget_counts)) if nontarget_counts else 0.0

    output = {
        "jalur": "CascadeEngine.predict",
        "sha256_checkpoint": sha256_ckpt,
        "pool": pool_info,
        "korpus": ["field/inat", "field/xc_noisy", "field/other", "uji_independen"],
        "agregat": {"presisi": round(presisi, 4), "recall": round(recall, 4)},
        "per_korpus": per_korpus,
        "per_spesies": per_spesies,
        "spesies_nontarget_per_berkas": round(spesies_nontarget_per_berkas, 4),
        "per_berkas": per_berkas,
        "gagal": gagal,
        "waktu_total_s": round(time.time() - t_start, 1),
    }

    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(output, indent=2, ensure_ascii=False))

    print(f"\nAgregat: presisi {presisi:.4f}, recall {recall:.4f}")
    print(f"Berkas dievaluasi: {len(per_berkas)}, gagal: {len(gagal)}")
    print(f"Waktu total: {time.time() - t_start:.0f}s")
    print(f"Output: {out_json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())