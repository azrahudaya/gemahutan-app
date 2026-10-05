"""Simulasi perkiraan lokasi (blok K): API tanpa menulis ke basis data.

Metode mengikuti proposal Bagian 7.3 dan berkas
`docs/assets/diagram_src/eksperimen_simulasi.py`: larik 4 mikrofon bujur
sangkar 0,5 m, arah dihitung dengan GCC-PHAT (`ml.localization.estimasi_arah`),
jarak kasar dari selisih level, lalu beberapa arah digabung dengan
`triangulasi`. Ini simulasi sinyal tanpa gema, jadi hasilnya batas atas mutu,
bukan angka lapangan.
"""
from math import atan2, degrees, hypot

import numpy as np
from fastapi import APIRouter, Depends, HTTPException

from app.deps import get_current_user
from app.models.tables import User
from app.schemas.simulasi import (
    ArahAlat,
    SimulasiLokasiRequest,
    SimulasiLokasiResponse,
)
from ml.localization import (
    bangun_sintetis,
    estimasi_arah,
    jarak_dari_selisih_level,
    triangulasi,
)

router = APIRouter(prefix="/api/v1/simulasi", tags=["simulasi"])

# Larik 4 mikrofon bujur sangkar 0,5 m, sama dengan acuan proposal.
LARIK = [(-0.25, -0.25), (0.25, -0.25), (0.25, 0.25), (-0.25, 0.25)]
SR = 16000
# Level sumber pada jarak referensi. Simulasi memakai penyusutan bebas medan
# 6 dB per dua kali lipat jarak, sama dengan asumsi `jarak_dari_selisih_level`.
LEVEL_REFERENSI_DB = 60.0
JARAK_REFERENSI_M = 1.0
# Batas supaya hitungan tetap cepat dan permintaan tidak menahan worker API.
MAKS_ALAT = 4
KOTAK_TRIANGULASI_M = 120.0
LANGKAH_TRIANGULASI_M = 1.0


def _arah_dan_jarak(dari: tuple[float, float], ke: tuple[float, float]) -> tuple[float, float]:
    dx, dy = ke[0] - dari[0], ke[1] - dari[1]
    return float(degrees(atan2(dy, dx)) % 360), float(hypot(dx, dy))


def _derau_level_db(snr_db: float) -> float:
    """Simpangan baku derau pengukuran level (dB) dari SNR.

    SNR 0 dB memberi derau 3 dB, dan tiap kenaikan 20 dB menurunkan derau
    sepuluh kali lipat. Ini model kasar, cukup untuk menunjukkan rentang.
    """
    if snr_db <= 0:
        return 3.0
    return 3.0 * (10 ** (-snr_db / 20.0))


@router.post("/lokasi", response_model=SimulasiLokasiResponse)
async def simulasi_lokasi(
    body: SimulasiLokasiRequest,
    current_user: User = Depends(get_current_user),
):
    """Hitung arah dan area perkiraan dari alat virtual dan satu sumber.

    Tidak menulis ke basis data. Semua peran petugas boleh memakainya.
    """
    alat = body.alat
    if not 2 <= len(alat) <= MAKS_ALAT:
        raise HTTPException(400, f"Jumlah alat harus 2 sampai {MAKS_ALAT}.")
    if not 0 <= body.snr_db <= 60:
        raise HTTPException(400, "SNR harus antara 0 sampai 60 dB.")
    sx, sy = body.sumber
    if not all(np.isfinite(v) for v in (sx, sy)):
        raise HTTPException(400, "Posisi sumber tidak valid.")
    for a in alat:
        if not all(np.isfinite(v) for v in (a.x, a.y)):
            raise HTTPException(400, "Posisi alat tidak valid.")
        if a.jenis not in ("larik", "satu_kanal"):
            raise HTTPException(400, "Jenis alat harus 'larik' atau 'satu_kanal'.")

    rng = np.random.default_rng(body.benih)
    arah_hasil: list[ArahAlat] = []
    arah_untuk_triangulasi: list[tuple[float, float, float]] = []

    for i, alat_satu in enumerate(alat):
        az_benar, jarak_benar = _arah_dan_jarak((alat_satu.x, alat_satu.y), (sx, sy))
        azimuth = None
        keyakinan = None
        kembar: list[float] = []

        if alat_satu.jenis == "larik":
            sinyal = bangun_sintetis(
                az_benar, jarak_benar, LARIK, sr=SR,
                snr_db=body.snr_db, benih=body.benih * 10 + i,
            )
            hasil = estimasi_arah(sinyal, SR, LARIK)
            if hasil is not None:
                azimuth = hasil.azimuth_deg
                keyakinan = hasil.keyakinan
                kembar = [float(k) for k in hasil.arah_kembar]
                # Jam tidak sinkron menggeser arah yang diukur.
                if not body.sinkron:
                    azimuth = (azimuth + float(rng.normal(0.0, 5.0))) % 360
                arah_untuk_triangulasi.append((alat_satu.x, alat_satu.y, azimuth))

        # Jarak kasar dari selisih level, dengan derau sesuai SNR.
        level_ukur = LEVEL_REFERENSI_DB - 20 * np.log10(max(jarak_benar, 1e-3) / JARAK_REFERENSI_M)
        level_ukur += float(rng.normal(0.0, _derau_level_db(body.snr_db)))
        jarak_estimasi = jarak_dari_selisih_level(
            level_ukur, LEVEL_REFERENSI_DB, JARAK_REFERENSI_M
        )

        arah_hasil.append(
            ArahAlat(
                x=alat_satu.x,
                y=alat_satu.y,
                azimuth_deg=round(azimuth, 1) if azimuth is not None else None,
                keyakinan=round(keyakinan, 3) if keyakinan is not None else None,
                azimuth_kembar=[round(k, 1) for k in kembar],
                jarak_estimasi_m=round(jarak_estimasi, 1) if jarak_estimasi is not None else None,
            )
        )

    perkiraan = None
    galat_m = None
    radius_area_m = None
    catatan = "sinyal buatan tanpa gema; area perkiraan adalah lingkaran di sekitar titik hasil triangulasi"
    if len(arah_untuk_triangulasi) >= 2:
        pos = triangulasi(arah_untuk_triangulasi, kotak_m=KOTAK_TRIANGULASI_M, langkah_m=LANGKAH_TRIANGULASI_M)
        perkiraan = (round(pos.x_m, 1), round(pos.y_m, 1))
        galat_m = float(hypot(pos.x_m - sx, pos.y_m - sy))
        radius_area_m = round(max(galat_m, 3.0) * 2.0, 1)
    else:
        catatan = "kurang dari dua alat larik memberi arah, jadi tidak ada area perkiraan"

    return SimulasiLokasiResponse(
        arah=arah_hasil,
        perkiraan=perkiraan,
        radius_area_m=radius_area_m,
        galat_m=round(galat_m, 1) if galat_m is not None else None,
        sumber=(sx, sy),
        jumlah_alat=len(alat),
        sinkron=body.sinkron,
        catatan=catatan,
    )
