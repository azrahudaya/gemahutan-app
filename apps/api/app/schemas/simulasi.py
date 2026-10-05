"""Skema simulasi perkiraan lokasi (blok K).

Simulasi ini tidak menulis ke basis data. Pengguna menaruh 2 sampai 4 alat
virtual dan satu titik sumber suara, lalu API menghitung arah dari tiap alat
dan menggabungkannya menjadi area perkiraan. Semua angka dalam meter.
"""
from pydantic import BaseModel


class AlatSimulasi(BaseModel):
    x: float
    y: float
    # "larik" = 4 mikrofon bujur sangkar 0,5 m (bisa mengukur arah); "satu_kanal"
    # = satu mikrofon (tidak bisa mengukur arah, hanya jarak kasar).
    jenis: str = "larik"


class SimulasiLokasiRequest(BaseModel):
    alat: list[AlatSimulasi]
    sumber: tuple[float, float]
    snr_db: float = 20.0
    benih: int = 0
    sinkron: bool = True


class ArahAlat(BaseModel):
    x: float
    y: float
    azimuth_deg: float | None
    keyakinan: float | None
    azimuth_kembar: list[float] = []
    jarak_estimasi_m: float | None


class SimulasiLokasiResponse(BaseModel):
    arah: list[ArahAlat]
    perkiraan: tuple[float, float] | None
    radius_area_m: float | None
    galat_m: float | None
    sumber: tuple[float, float]
    jumlah_alat: int
    sinkron: bool
    catatan: str
