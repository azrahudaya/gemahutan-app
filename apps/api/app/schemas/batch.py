"""Skema unggah batch: satu berkas gagal tidak membatalkan berkas lain."""
from pydantic import BaseModel


class BatchItemResult(BaseModel):
    filename: str
    recording_id: int | None = None
    status: str
    error: str | None = None


class BatchUploadResponse(BaseModel):
    batch_id: str
    count: int
    accepted: int
    failed: int
    items: list[BatchItemResult]


class BatchSummary(BaseModel):
    batch_id: str
    created_at: str | None = None
    total: int
    done: int
    failed: int
    progress_percent: int


class BatchRecordingItem(BaseModel):
    id: int
    filename: str
    status: str
    progress: int
    stage: str | None = None


class BatchDetailResponse(BaseModel):
    batch_id: str
    total: int
    done: int
    failed: int
    pending: int
    processing: int
    progress_percent: int
    recordings: list[BatchRecordingItem]
