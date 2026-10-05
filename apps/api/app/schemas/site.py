
from pydantic import BaseModel, Field


class SiteCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    latitude: float | None = Field(None, ge=-90, le=90)
    longitude: float | None = Field(None, ge=-180, le=180)
    location: str | None = Field(None, max_length=255)
    habitat_type: str | None = Field(None, max_length=100)
    elevation_m: float | None = None
    description: str | None = None
    notes: str | None = None


class SiteUpdate(BaseModel):
    """Kolom lokasi yang boleh dikoreksi. Semua opsional, hanya yang dikirim diubah."""

    name: str | None = Field(None, min_length=2, max_length=255)
    latitude: float | None = Field(None, ge=-90, le=90)
    longitude: float | None = Field(None, ge=-180, le=180)
    location: str | None = Field(None, max_length=255)
    habitat_type: str | None = Field(None, max_length=100)
    elevation_m: float | None = None
    description: str | None = None
    notes: str | None = None


class SiteResponse(BaseModel):
    id: int
    name: str
    latitude: float | None = None
    longitude: float | None = None
    location: str | None = None
    habitat_type: str | None = None
    elevation_m: float | None = None
    description: str | None = None
    notes: str | None = None
    status: str
    recordings_count: int = 0
    detections_count: int = 0
    species_count: int = 0
    last_recording_at: str | None = None
    created_at: str | None = None
    # True kalau lokasi punya deteksi spesies prioritas dan koordinatnya sudah
    # dibulatkan untuk melindungi lokasi burung langka.
    lokasi_disamarkan: bool = False
