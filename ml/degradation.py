"""Bangun tangga degradasi audio dari klip uji bersih memakai ffmpeg.

Desainnya berbasis SNR yang terukur, bukan atenuasi desibel sembarang: tiap klip
diukur dulu RMS-nya, lalu derau disetel supaya perbandingan sinyal terhadap derau
sesuai target. Tanpa ini, klip berlevel rendah akan berubah jadi nyaris sunyi dan
yang terukur malah keheningan, bukan pengaruh gangguan.

Untuk tingkat jarak, audio dinormalkan dulu (dynaudnorm) sebelum disaring dan
dilemahkan, supaya yang diuji benar-benar pengaruh jarak.

Ini SIMULASI, bukan rekaman lapangan, dan harus dilabeli begitu di laporan.

Pakai:
    cd ml && ../.venv/bin/python degradation.py
    cd ml && ../.venv/bin/python degradation.py --tiers jarak_30m,jarak_100m
"""
import argparse
import csv
import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

ML_DIR = Path(__file__).resolve().parent
DATA_DIR = ML_DIR / "data"
MANIFEST = DATA_DIR / "manifest.csv"
SPLITS = DATA_DIR / "splits.json"
OUT_DIR = DATA_DIR / "degraded"
PARAMS = OUT_DIR / "params.json"

# snr_db: target perbandingan sinyal terhadap derau. None berarti tanpa derau.
# rantai_sumber: filter yang dikenakan ke audio asli sebelum derau dicampur.
TIERS: dict[str, dict] = {
    "kontrol_reencode": {
        "keterangan": "kontrol tanpa gangguan: mengukur batas bawah pipeline sendiri",
        "derau": [],
        "rantai_sumber": "aformat=channel_layouts=mono,aresample=48000",
    },
    "hujan_ringan": {
        "keterangan": "hujan ringan, target SNR +10 dB",
        "derau": [{"jenis": "pink", "snr_db": 10.0, "filter": "tremolo=f=0.4:d=0.6"}],
        "rantai_sumber": "aformat=channel_layouts=mono,aresample=48000",
    },
    "hujan_deras": {
        "keterangan": "hujan deras, target SNR 0 dB",
        "derau": [{"jenis": "pink", "snr_db": 0.0, "filter": "tremolo=f=0.7:d=0.8"}],
        "rantai_sumber": "aformat=channel_layouts=mono,aresample=48000",
    },
    "angin": {
        "keterangan": "angin, target SNR +6 dB, derau disaring di bawah 400 Hz",
        "derau": [{"jenis": "brown", "snr_db": 6.0, "filter": "lowpass=f=400,tremolo=f=0.15:d=0.8"}],
        "rantai_sumber": "aformat=channel_layouts=mono,aresample=48000",
    },
    "kota": {
        "keterangan": "kebisingan kota, target SNR 0 dB, ada gemuruh 70 Hz",
        "derau": [
            {"jenis": "brown", "snr_db": 0.0, "filter": "lowpass=f=3000"},
            {"jenis": "sine70", "snr_db": 12.0, "filter": "anull"},
        ],
        "rantai_sumber": "aformat=channel_layouts=mono,aresample=48000",
    },
    "jarak_30m": {
        "keterangan": "jarak 30 m: dinormalkan, lowpass 5 kHz, -6 dB, gaung pendek, "
                      "latar derau SNR +20 dB",
        "derau": [{"jenis": "pink", "snr_db": 20.0, "filter": "lowpass=f=2000"}],
        "rantai_sumber": ("aformat=channel_layouts=mono,aresample=48000,"
                          "dynaudnorm=f=250:g=15,lowpass=f=5000,volume=-6dB,"
                          "aecho=0.7:0.6:60:0.3"),
    },
    "jarak_100m": {
        "keterangan": "jarak 100 m: dinormalkan, lowpass 2.5 kHz, -12 dB, gaung panjang, "
                      "latar derau SNR +20 dB",
        "derau": [{"jenis": "pink", "snr_db": 20.0, "filter": "lowpass=f=1200"}],
        "rantai_sumber": ("aformat=channel_layouts=mono,aresample=48000,"
                          "dynaudnorm=f=250:g=15,lowpass=f=2500,volume=-12dB,"
                          "aecho=0.8:0.7:120:0.4"),
    },
    "gabungan_berat": {
        "keterangan": "kondisi terberat: hujan SNR 0 dB plus jarak 100 m",
        "derau": [{"jenis": "pink", "snr_db": 0.0, "filter": "tremolo=f=0.7:d=0.8"}],
        "rantai_sumber": ("aformat=channel_layouts=mono,aresample=48000,"
                          "dynaudnorm=f=250:g=15,lowpass=f=2500,volume=-12dB,"
                          "aecho=0.8:0.7:120:0.4"),
    },
}

_FAKTOR_DERAU: dict[str, float] = {}
_RMS_CACHE: dict[str, float] = {}


def rms_berkas(berkas: Path) -> float:
    """RMS berkas, di-cache supaya tidak dihitung berulang untuk klip yang sama."""
    kunci = str(berkas)
    if kunci in _RMS_CACHE:
        return _RMS_CACHE[kunci]
    import librosa

    try:
        y, _ = librosa.load(str(berkas), sr=48000, mono=True)
        nilai = float(np.sqrt(np.mean(y ** 2))) if len(y) else 0.0
    except Exception:
        nilai = 0.0
    _RMS_CACHE[kunci] = nilai
    return nilai


def faktor_derau(jenis: str) -> float:
    """Ukur RMS derau untuk amplitudo 1.0, supaya level derau bisa dihitung tepat."""
    if jenis in _FAKTOR_DERAU:
        return _FAKTOR_DERAU[jenis]
    lavfi = {
        "pink": "anoisesrc=color=pink:amplitude=1.0:d=3",
        "brown": "anoisesrc=color=brown:amplitude=1.0:d=3",
        "sine70": "sine=frequency=70:duration=3",
    }[jenis]
    proses = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i", lavfi,
         "-f", "f32le", "-ac", "1", "-ar", "48000", "-"],
        capture_output=True,
    )
    if proses.returncode != 0 or not proses.stdout:
        _FAKTOR_DERAU[jenis] = 1.0
        return 1.0
    data = np.frombuffer(proses.stdout, dtype=np.float32)
    faktor = float(np.sqrt(np.mean(data ** 2))) or 1.0
    _FAKTOR_DERAU[jenis] = faktor
    return faktor


def klip_uji() -> list[dict]:
    split = json.loads(SPLITS.read_text())
    id_uji = set(split["test"])
    with MANIFEST.open() as fh:
        return [r for r in csv.DictReader(fh) if r["clip_id"] in id_uji]


def bangun_perintah(sumber: Path, tujuan: Path, tier: dict, rms_sumber: float,
                    batas_detik: float | None = None) -> list[str]:
    """Susun perintah ffmpeg untuk satu klip.

    batas_detik memotong keluaran ke durasi yang benar-benar dibaca model (3 detik),
    supaya data simulasi tidak menghabiskan ruang berkali-kali lipat tanpa guna.
    """
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(sumber)]
    derau = tier.get("derau", [])

    amplitudo = []
    for d in derau:
        target_rms = rms_sumber / (10 ** (d["snr_db"] / 20)) if rms_sumber > 0 else 0.0
        amplitudo.append(round(max(target_rms / faktor_derau(d["jenis"]), 1e-6), 6))

    for d, amp in zip(derau, amplitudo, strict=True):
        if d["jenis"] == "sine70":
            cmd += ["-f", "lavfi", "-i", "sine=frequency=70:duration=900"]
        else:
            cmd += ["-f", "lavfi", "-i", f"anoisesrc=color={d['jenis']}:amplitude={amp}:d=900"]

    rantai = [f"[0:a]{tier['rantai_sumber']}[src]"]
    label = "[src]"
    for idx, (d, amp) in enumerate(zip(derau, amplitudo, strict=True), start=1):
        if d["jenis"] == "sine70":
            # Sine tidak punya parameter amplitudo, jadi levelnya diatur lewat volume.
            rantai.append(f"[{idx}:a]volume={amp:.6f}[d{idx}]")
        else:
            rantai.append(f"[{idx}:a]{d['filter']}[d{idx}]")
        keluaran = "[mix]" if idx == len(derau) else f"[tmp{idx}]"
        rantai.append(f"{label}[d{idx}]amix=inputs=2:duration=first:normalize=0{keluaran}")
        label = keluaran
    if derau:
        rantai.append(f"{label}alimiter=limit=0.95:level=0[out]")
    else:
        rantai.append("[src]alimiter=limit=0.95:level=0[out]")
    if batas_detik:
        cmd += ["-t", str(batas_detik)]
    cmd += ["-filter_complex", ";".join(rantai), "-map", "[out]",
            "-ar", "48000", "-ac", "1", str(tujuan)]
    return cmd


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tiers", default=",".join(TIERS))
    parser.add_argument("--ganti", action="store_true", help="timpa berkas yang sudah ada")
    parser.add_argument("--batas-detik", type=float, default=None,
                        help="potong audio ke detik ini (mis. 3 = model slice)")
    parser.add_argument("--sampel", type=int, default=None,
                        help="acak dan ambil N klip dari test set saja")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    if not shutil.which("ffmpeg"):
        print("ffmpeg tidak ada di PATH")
        return 1

    pilihan = [t.strip() for t in args.tiers.split(",") if t.strip() in TIERS]
    klip = klip_uji()
    if args.sampel is not None and args.sampel < len(klip):
        import random
        rnd = random.Random(args.seed)
        klip = rnd.sample(klip, args.sampel)
    print(f"klip uji: {len(klip)} | tingkat: {len(pilihan)}"
          + (f" | batas_detik={args.batas_detik}s" if args.batas_detik else ""))
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    for jenis in ("pink", "brown", "sine70"):
        print(f"  faktor derau {jenis}: {faktor_derau(jenis):.4f}")

    ringkas = {}
    for nama in pilihan:
        tier = TIERS[nama]
        folder = OUT_DIR / nama
        folder.mkdir(parents=True, exist_ok=True)
        berhasil = 0
        for rec in klip:
            # local_path di manifest relatif terhadap ml/data/
            sumber = DATA_DIR / rec["local_path"]
            if not sumber.exists():
                continue
            tujuan = folder / f"{rec['clip_id']}.wav"
            if tujuan.exists() and not args.ganti:
                berhasil += 1
                continue
            rms = rms_berkas(sumber)
            hasil = subprocess.run(bangun_perintah(sumber, tujuan, tier, rms,
                                                  batas_detik=args.batas_detik),
                                   capture_output=True, text=True)
            if hasil.returncode == 0 and tujuan.exists():
                berhasil += 1
            else:
                print(f"    gagal {rec['clip_id']} pada {nama}: {hasil.stderr.strip()[:80]}")
        ringkas[nama] = berhasil
        print(f"  {nama}: {berhasil}/{len(klip)} berkas")
        PARAMS.write_text(json.dumps({
            "catatan": "Simulasi degradasi, bukan rekaman lapangan",
            "desain": "derau disetel terhadap SNR terukur dari tiap klip",
            "sample_rate": 48000,
            "channels": 1,
            "faktor_derau_amplitudo_1": _FAKTOR_DERAU,
            "sumber_klip": "ml/data/splits.json bagian test",
            "tingkat": TIERS,
            "jumlah_berkas": ringkas,
        }, indent=2, ensure_ascii=False))
    print(f"parameter tersimpan di {PARAMS.relative_to(ML_DIR.parent)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
