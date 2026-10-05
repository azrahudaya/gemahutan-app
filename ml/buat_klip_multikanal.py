"""Buat klip demo banyak kanal dengan arah datang yang diketahui.

Klip nyata dari ml/demo_audio disalin ke sejumlah kanal, lalu tiap kanal digeser
sesuai selisih waktu tiba teori untuk satu azimuth. Geseran dihitung memakai
tdoa_teori dari ml/localization.py, jadi berkas uji dan estimator memakai
geometri serta kecepatan suara yang sama. Alasannya sederhana: arah hanya bisa
diuji kalau arah sebenarnya diketahui, dan klip lapangan tidak menyimpannya.

Pemakaian:
    python ml/buat_klip_multikanal.py --masuk ml/demo_audio/xc-105148.mp3 \
        --keluar /tmp/uji_4kanal.wav --azimuth 60 --spacing 0.5 --kanal 4 --durasi 12
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ml.localization import estimasi_arah, tdoa_teori  # noqa: E402


def geometri_linier(jumlah_kanal: int, spacing_m: float) -> list[tuple[float, float]]:
    """Mikrofon berbaris di sumbu x, kanal i di x = i kali jarak antar mikrofon."""
    return [(i * spacing_m, 0.0) for i in range(jumlah_kanal)]


def bangun_klip(mono: np.ndarray, sr: int, azimuth_deg: float, spacing_m: float,
                jumlah_kanal: int) -> tuple[np.ndarray, list[float]]:
    """Salin mono ke beberapa kanal dengan geseran waktu tiba per kanal."""
    geometri = geometri_linier(jumlah_kanal, spacing_m)
    teori = tdoa_teori(azimuth_deg, geometri)

    # teori[(0, i)] adalah waktu tiba kanal 0 dikurangi kanal i, jadi tunda
    # kanal i terhadap kanal 0 adalah kebalikannya. Tunda positif berarti kanal
    # itu menerima suara lebih lambat.
    tunda_s = [0.0] + [-teori[(0, i)] for i in range(1, jumlah_kanal)]

    n = mono.shape[0]
    keluaran = np.zeros((n, jumlah_kanal), dtype=np.float32)
    for i, tunda in enumerate(tunda_s):
        geser = int(round(tunda * sr))
        if geser >= 0:
            keluaran[geser:, i] = mono[: n - geser]
        else:
            keluaran[: n + geser, i] = mono[-geser:]
    return keluaran, tunda_s


def main() -> int:
    parser = argparse.ArgumentParser(description="Buat klip demo banyak kanal")
    parser.add_argument("--masuk", required=True)
    parser.add_argument("--keluar", required=True)
    parser.add_argument("--azimuth", type=float, required=True)
    parser.add_argument("--spacing", type=float, default=0.5)
    parser.add_argument("--kanal", type=int, default=4)
    parser.add_argument("--durasi", type=float, default=0.0)
    parser.add_argument("--mulai", type=float, default=0.0)
    args = parser.parse_args()

    import soundfile as sf

    data, sr = sf.read(args.masuk, always_2d=True, dtype="float32")
    mono = data.mean(axis=1)
    awal = int(args.mulai * sr)
    akhir = data.shape[0] if args.durasi <= 0 else min(data.shape[0], int((args.mulai + args.durasi) * sr))
    mono = mono[awal:akhir]
    if mono.size == 0:
        print("bagian audio yang dipilih kosong", file=sys.stderr)
        return 1

    keluaran, tunda_s = bangun_klip(mono, sr, args.azimuth, args.spacing, args.kanal)

    keluar = Path(args.keluar)
    keluar.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(keluar), keluaran, sr, subtype="PCM_16")

    # Periksa ulang hasil tulis: kalau geseran salah, azimuthnya meleset jauh
    # dan itu harus kelihatan sebelum berkasnya diunggah.
    baca, sr_baca = sf.read(str(keluar), always_2d=True, dtype="float32")
    hasil = estimasi_arah(
        [baca[:, i] for i in range(baca.shape[1])],
        sr_baca,
        geometri_linier(baca.shape[1], args.spacing),
    )

    ringkas = {
        "berkas": str(keluar),
        "azimuth_sesungguhnya_deg": args.azimuth,
        "kanal": int(baca.shape[1]),
        "sample_rate": int(sr_baca),
        "durasi_s": round(baca.shape[0] / sr_baca, 3),
        "spacing_m": args.spacing,
        "tunda_ms_per_kanal": [round(t * 1000.0, 3) for t in tunda_s],
        "azimuth_terukur_deg": None if hasil is None else round(hasil.azimuth_deg, 2),
        "galat_deg": None if hasil is None else round(
            abs((hasil.azimuth_deg - args.azimuth + 180) % 360 - 180), 2
        ),
    }
    print(json.dumps(ringkas, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
