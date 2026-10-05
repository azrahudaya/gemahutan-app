"""Uji modul lokalisasi memakai rekaman buatan dengan arah dan jarak yang diketahui."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ml.localization import (  # noqa: E402
    bangun_sintetis,
    estimasi_arah,
    jarak_dari_selisih_level,
    triangulasi,
)

SR = 16000
# Empat mikrofon pada bujur sangkar 0,5 m, titik nol di pusat array.
ARRAY_0_5_M = [(-0.25, -0.25), (0.25, -0.25), (0.25, 0.25), (-0.25, 0.25)]
# Bentuk T dengan bentang 1,2 m, lebih tajam untuk sudut depan dan belakang.
ARRAY_T_1_2_M = [(-0.6, 0.0), (0.0, 0.0), (0.6, 0.0), (0.0, 0.6)]


def galat_arah(geometri, azimuth, snr_db, benih):
    kanal = bangun_sintetis(azimuth, 25.0, geometri, sr=SR, snr_db=snr_db, benih=benih)
    hasil = estimasi_arah(kanal, SR, geometri)
    selisih = abs((hasil.azimuth_deg - azimuth + 180) % 360 - 180)
    return selisih, hasil


def main() -> None:
    print("Array 0,5 m (bujur sangkar), sumber 25 m")
    print(f"{'SNR':>6} {'galat median':>14} {'galat maks':>12} {'keyakinan':>10}")
    for snr in (30, 20, 10, 5, 0, -5):
        galat = [galat_arah(ARRAY_0_5_M, az, snr, b)[0] for az in (0, 45, 90, 135, 180, 225, 270, 315) for b in (1, 2)]
        yak = np.mean([galat_arah(ARRAY_0_5_M, az, snr, b)[1].keyakinan for az in (0, 90, 180, 270) for b in (1, 2)])
        print(f"{snr:>6} {np.median(galat):>13.1f}d {np.max(galat):>11.1f}d {yak:>10.2f}")

    print()
    print("Array T bentang 1,2 m, sumber 25 m")
    print(f"{'SNR':>6} {'galat median':>14} {'galat maks':>12}")
    for snr in (20, 10, 5, 0):
        galat = [galat_arah(ARRAY_T_1_2_M, az, snr, b)[0] for az in (0, 45, 90, 135, 180, 225, 270, 315) for b in (1, 2)]
        print(f"{snr:>6} {np.median(galat):>13.1f}d {np.max(galat):>11.1f}d")

    print()
    print("Jarak dari penyusutan amplitudo, kalibrasi di 10 m")
    for galat_db in (3, 6, 10):
        jarak = jarak_dari_selisih_level(-6.0 - galat_db, -6.0, 10.0)
        print(f"  salah taksir level sumber {galat_db:>2} dB: sumber 10 m terbaca {jarak:>5.1f} m")

    print()
    tes = []
    tes.append(("arah pada SNR 10 dB meleset di bawah 5 derajat", np.median([galat_arah(ARRAY_0_5_M, az, 10, 1)[0] for az in range(0, 360, 15)]) < 5.0))
    tes.append(("arah pada SNR 0 dB meleset di bawah 10 derajat", np.median([galat_arah(ARRAY_0_5_M, az, 0, 1)[0] for az in range(0, 360, 15)]) < 10.0))
    # Galat arah 3 derajat adalah angka realistis dari pengukuran di atas;
    # dua perangkat memberi titik potong yang jauh lebih kasar daripada tiga.
    def meleset(perangkat, sigma, benih):
        rng = np.random.default_rng(benih)
        pasangan = []
        for x0, y0 in perangkat:
            az = float(np.degrees(np.arctan2(120.0 - y0, 40.0 - x0)))
            pasangan.append((x0, y0, az + rng.normal(0, sigma)))
        hasil = triangulasi(pasangan)
        return float(np.hypot(hasil.x_m - 40.0, hasil.y_m - 120.0))

    dua = [(0.0, 0.0), (300.0, 0.0)]
    tiga = [(0.0, 0.0), (300.0, 0.0), (200.0, 300.0)]
    sebaran_dua = [meleset(dua, 3, b) for b in range(20)]
    sebaran_tiga = [meleset(tiga, 3, b) for b in range(20)]
    print(
        "Sebaran meleset pada galat arah 3 derajat: "
        f"dua perangkat median {np.median(sebaran_dua):.1f} m dan terburuk {np.max(sebaran_dua):.1f} m, "
        f"tiga perangkat median {np.median(sebaran_tiga):.1f} m dan terburuk {np.max(sebaran_tiga):.1f} m"
    )
    # Dua perangkat dinilai dari median karena ekor sebarannya panjang, satu
    # undian sudut yang meleset sudah melempar titik potong puluhan meter.
    tes.append(("triangulasi dua perangkat, median meleset di bawah 25 m", float(np.median(sebaran_dua)) < 25.0))
    tes.append(("triangulasi tiga perangkat, terburuk meleset di bawah 35 m", float(np.max(sebaran_tiga)) < 35.0))
    print("Ringkasan uji")
    for nama, lulus in tes:
        print(f"  [{'LULUS' if lulus else 'GAGAL'}] {nama}")

    print()
    print("Triangulasi dua perangkat, jarak antar perangkat 300 m, sumber di (40, 120)")
    for galat_sudut in (0, 3, 8):
        rng = np.random.default_rng(7)
        pasangan = []
        for x0, y0 in ((0.0, 0.0), (300.0, 0.0)):
            benar = np.degrees(np.arctan2(120.0 - y0, 40.0 - x0))
            pasangan.append((x0, y0, benar + rng.normal(0, galat_sudut)))
        hasil = triangulasi(pasangan)
        selisih = float(np.hypot(hasil.x_m - 40.0, hasil.y_m - 120.0))
        print(f"  galat arah {galat_sudut:>2} derajat: titik terbaca ({hasil.x_m:.0f}, {hasil.y_m:.0f}), meleset {selisih:.0f} m")


if __name__ == "__main__":
    main()
