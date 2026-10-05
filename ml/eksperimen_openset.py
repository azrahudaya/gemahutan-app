"""Eksperimen open-set: sapu konfigurasi cascade pada subset 'pilih'.

Hanya berkas bagian 'pilih' dipakai untuk memilih. FP pengecoh dan recall
target diukur pada 'pilih'. Konfigurasi terbaik lalu dilaporkan di 'lapor'.

Jalankan: python3 ml/eksperimen_openset.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

ML_DIR = ROOT / "ml"
E2E = ML_DIR / "reports" / "e2e.json"
CONFIG_FILE = ML_DIR / "configs" / "cascade.yaml"
CACHE_E2E = ML_DIR / "data" / "cache_e2e"
FIELD_AUDIO = ML_DIR / "data" / "field" / "audio"
INDEP_AUDIO = ML_DIR / "data" / "uji_independen" / "audio"
PEMBAGIAN = ML_DIR / "data" / "pembagian_openset.json"
REPORTS = ML_DIR / "reports"

AUDIO_EXT = {".wav", ".mp3", ".m4a", ".ogg", ".flac", ".opus", ".webm", ".aac"}
BUTUH_KONVERSI = {".m4a", ".ogg", ".opus", ".webm", ".aac", ".flac"}


def muat_pembagian():
    return json.loads(PEMBAGIAN.read_text())


def species_dari_folder(name):
    return name.replace('_', ' ')


def konversi_ke_wav(path):
    import subprocess
    wav = CACHE_E2E / f"{path.stem}.wav"
    if wav.exists():
        return wav
    try:
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(path),
                        "-ar", "48000", "-ac", "1", str(wav)],
                       check=True, timeout=120, capture_output=True)
        return wav
    except Exception:
        return None


def daftar_pilih():
    """Berkas bagian 'pilih' saja (target pilih + pengecoh pilih)."""
    pembagian = muat_pembagian()
    sp_pilih = set(pembagian["spesies_pengecoh_pilih"])
    berkas_pilih = set(pembagian["berkas_target_pilih"])

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
                if f.is_dir() or f.suffix.lower() not in AUDIO_EXT:
                    continue
                local = str(f.relative_to(ML_DIR / "data"))
                if korpus == "other":
                    # Nama folder snake_case dipakai untuk pengecoh
                    bagian = "pilih" if sub.name in sp_pilih else "lapor"
                else:
                    bagian = "pilih" if local in berkas_pilih else "lapor"
                if bagian != "pilih":
                    continue
                if korpus == "other":
                    out.append((f, "pengecoh", []))
                else:
                    out.append((f, "target", [sp]))
    return out


def ukur(engine, berkas):
    """Ukur FP pengecoh dan recall target."""
    fp_berkas = 0
    n_pengecoh = 0
    tp_berkas = 0
    n_target = 0
    for path, jenis, benar in berkas:
        try:
            if path.suffix.lower() in BUTUH_KONVERSI:
                proses = konversi_ke_wav(path)
                if proses is None:
                    continue
            else:
                proses = path
            hasil = engine.predict(str(proses))
            target_deteksi = {d.species_scientific for d in hasil
                              if d.species_scientific in engine._indonesian_species}
            if jenis == "pengecoh":
                n_pengecoh += 1
                if target_deteksi:
                    fp_berkas += 1
            else:
                n_target += 1
                if benar and benar[0] in target_deteksi:
                    tp_berkas += 1
        except Exception:
            continue
    fp_rate = fp_berkas / n_pengecoh if n_pengecoh else 0.0
    recall = tp_berkas / n_target if n_target else 0.0
    return fp_rate, recall, n_pengecoh, n_target


def tulis_config(cfg):
    CONFIG_FILE.write_text(yaml.safe_dump(cfg, allow_unicode=True))


def main():
    from ml.engines.cascade import CascadeEngine

    berkas = daftar_pilih()
    print(f"Berkas pilih: {len(berkas)}")

    # Bersihkan cache (config berubah -> deteksi berubah)
    for f in CACHE_E2E.glob("*.json"):
        f.unlink()

    engine = CascadeEngine()

    # Kandidat konfigurasi
    kandidat = [
        {"nama": "baseline (0.1, no birdnet confirm)",
         "ambang_birdnet_nontarget": 0.1, "trackb_wajib_birdnet": False, "margin_top1_top2": 0.0},
        {"nama": "nontarget 0.3",
         "ambang_birdnet_nontarget": 0.3, "trackb_wajib_birdnet": False, "margin_top1_top2": 0.0},
        {"nama": "nontarget 0.5",
         "ambang_birdnet_nontarget": 0.5, "trackb_wajib_birdnet": False, "margin_top1_top2": 0.0},
        {"nama": "nontarget 0.5 + birdnet confirm",
         "ambang_birdnet_nontarget": 0.5, "trackb_wajib_birdnet": True, "margin_top1_top2": 0.0},
        {"nama": "nontarget 0.5 + margin 0.2",
         "ambang_birdnet_nontarget": 0.5, "trackb_wajib_birdnet": False, "margin_top1_top2": 0.2},
        {"nama": "nontarget 0.5 + margin 0.3",
         "ambang_birdnet_nontarget": 0.5, "trackb_wajib_birdnet": False, "margin_top1_top2": 0.3},
        {"nama": "nontarget 0.5 + margin 0.3 + confirm",
         "ambang_birdnet_nontarget": 0.5, "trackb_wajib_birdnet": True, "margin_top1_top2": 0.3},
    ]

    hasil = []
    for k in kandidat:
        cfg = {
            "ambang_birdnet_nontarget": k["ambang_birdnet_nontarget"],
            "trackb_wajib_birdnet": k["trackb_wajib_birdnet"],
            "margin_top1_top2": k["margin_top1_top2"],
        }
        tulis_config(cfg)
        engine._cfg = cfg
        # Bersihkan cache per konfigurasi
        for f in CACHE_E2E.glob("*.json"):
            f.unlink()
        fp_rate, recall, np_, nt = ukur(engine, berkas)
        hasil.append({"nama": k["nama"], "fp": round(fp_rate, 4),
                      "recall": round(recall, 4), "n_pengecoh": np_, "n_target": nt})
        print(f"  {k['nama']}: FP {fp_rate:.4f} ({np_}), recall {recall:.4f} ({nt})")

    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "openset_sweep.json").write_text(json.dumps(hasil, indent=2, ensure_ascii=False))
    print(f"\nOutput: {REPORTS / 'openset_sweep.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())