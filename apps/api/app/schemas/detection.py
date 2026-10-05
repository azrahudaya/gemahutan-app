
from pydantic import BaseModel


class DetectionResponse(BaseModel):
    id: int
    recording_id: int
    species_id: int
    species_name: str | None = None
    species_common: str | None = None
    confidence: float
    start_s: float
    end_s: float
    engine: str
    engine_version: str
    verified_status: str
    verified_by: int | None = None
    # Hasil lokalisasi apa adanya. Null berarti belum dihitung, bukan nol.
    azimuth_deg: float | None = None
    azimuth_confidence: float | None = None
    # Sudut cermin untuk susunan mikrofon segaris; 60 derajat dan 300 derajat
    # sama sah, dan itu batas susunannya, bukan keraguan pengukuran.
    azimuth_kembar_deg: float | None = None
    range_m: float | None = None
    localization_engine: str | None = None

    model_config = {"from_attributes": True}


class VerifyRequest(BaseModel):
    status: str  # correct, incorrect, uncertain


class PrioritasRequest(BaseModel):
    prioritas: bool


class SpeciesResponse(BaseModel):
    id: int
    scientific_name: str
    common_name_id: str | None
    common_name_en: str | None
    iucn_status: str | None
    ebird_code: str | None
    default_threshold: float
    detection_count: int | None = 0
    # True hanya untuk spesies yang punya kelas di classifier lokal. Sisanya
    # hanya bisa muncul dari penjaring BirdNET zero-shot, dan itu beda artinya
    # waktu dibaca pengguna.
    model_supported: bool = False
    # Prioritas konservasi: IUCN CR/EN/VU atau Permen LHK P.106/2018, atau
    # ditandai admin.
    prioritas: bool = False
    sumber_prioritas: str | None = None

    model_config = {"from_attributes": True}
