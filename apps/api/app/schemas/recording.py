from datetime import datetime

from pydantic import BaseModel


class RecordingCreate(BaseModel):
    site_id: int
    device_id: int | None = None
    recorded_at: datetime | None = None


class RecordingResponse(BaseModel):
    id: int
    site_id: int
    device_id: int | None
    uploaded_by: int
    storage_key: str
    filename: str | None = None
    batch_id: str | None = None
    site_name: str | None = None
    detection_count: int | None = 0
    duration_s: float | None
    sample_rate: int | None
    recorded_at: str | None
    status: str
    # Progres dan tahap diambil dari job pemrosesan rekaman ini. progress bernilai
    # 0 dan stage null kalau rekaman belum punya job sama sekali.
    progress: int = 0
    stage: str | None = None
    # Pesan galat pemrosesan kalau status failed; null kalau tidak ada.
    error_message: str | None = None
    created_at: str

    model_config = {"from_attributes": True}


class RecordingUpdate(BaseModel):
    """Kolom yang boleh dikoreksi setelah unggah.

    Isi audio dan hasil analisis tidak bisa diubah dari sini; kalau audionya
    salah, hapus lalu unggah ulang.
    """

    site_id: int | None = None
    device_id: int | None = None
    recorded_at: datetime | None = None


class RecordingListResponse(BaseModel):
    items: list[RecordingResponse]
    total: int
    page: int
    page_size: int
    total_pages: int = 1
