from datetime import datetime

from pydantic import BaseModel, Field


class AuditEntry(BaseModel):
    id: int
    actor_id: int | None
    actor_email: str | None
    # Nama tindakan yang bisa dibaca manusia, misal "Verifikasi deteksi".
    action: str
    entity_type: str | None
    entity_id: str | None
    detail: dict | None
    ip: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditListResponse(BaseModel):
    total: int = Field(description="Jumlah baris yang cocok dengan penyaring")
    items: list[AuditEntry]
    # Dikirim bersama daftar supaya pemanggil tidak perlu menebak nama tindakan
    # yang tersedia, dan bisa menyusun penyaringnya dari data nyata.
    actions: dict[str, str]
