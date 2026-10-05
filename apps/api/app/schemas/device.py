"""Skema perangkat akuisisi suara.

Kolom penting untuk lokalisasi adalah jumlah kanal dan jarak antar mikrofon:
tanpa dua nilai itu arah datang suara tidak bisa dihitung dari rekaman.
"""
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.tables import DeviceType


class DeviceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    type: DeviceType
    site_id: int
    serial: str | None = Field(default=None, max_length=120)
    channel_count: int = Field(default=1, ge=1, le=64)
    mic_spacing_m: float | None = Field(default=None, gt=0)
    reference_distance_m: float | None = Field(default=None, gt=0)
    reference_level_db: float | None = None
    installed_at: datetime | None = None
    notes: str | None = None


class DeviceUpdate(BaseModel):
    """Ubah sebagian kolom. Kolom yang tidak dikirim tidak disentuh."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    type: DeviceType | None = None
    site_id: int | None = None
    serial: str | None = Field(default=None, max_length=120)
    channel_count: int | None = Field(default=None, ge=1, le=64)
    mic_spacing_m: float | None = Field(default=None, gt=0)
    reference_distance_m: float | None = Field(default=None, gt=0)
    reference_level_db: float | None = None
    installed_at: datetime | None = None
    active: bool | None = None
    notes: str | None = None


class DeviceResponse(BaseModel):
    id: int
    name: str
    type: str
    site_id: int
    site_name: str | None = None
    serial: str | None = None
    channel_count: int
    mic_spacing_m: float | None = None
    reference_distance_m: float | None = None
    reference_level_db: float | None = None
    installed_at: str | None = None
    active: bool
    notes: str | None = None
    recording_count: int = 0


class DevicePilihan(BaseModel):
    """Daftar pendek perangkat untuk dipilih ranger saat rekam atau unggah.

    Ranger tidak butuh serial, jarak mikrofon, atau jumlah rekaman; cukup nama,
    lokasi, dan jumlah kanal. Kolom teknis lain tetap tertutup untuk ranger.
    """

    id: int
    name: str
    site_id: int
    site_name: str | None = None
    channel_count: int
    active: bool
