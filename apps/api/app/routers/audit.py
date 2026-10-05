"""Pembacaan jejak audit. Hanya admin.

Kenapa hanya admin: jejak ini memuat alamat IP dan riwayat tindakan tiap akun.
Itu alat pengawasan, dan kalau semua peran bisa membacanya, isinya bisa dipakai
untuk memantau rekan kerja alih-alih menelusuri masalah data.

Endpoint ini hanya membaca. Tidak ada jalur untuk mengubah atau menghapus baris
audit dari aplikasi, dan itu disengaja: jejak yang bisa disunting dari aplikasi
tidak bisa dipakai sebagai bukti.
"""
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db, require_admin
from app.models.tables import AuditLog, User
from app.schemas.audit import AuditEntry, AuditListResponse
from app.services.audit import AKSI

router = APIRouter(prefix="/api/v1/audit", tags=["audit"])

BATAS_MAKS = 200


@router.get("", response_model=AuditListResponse)
async def daftar_audit(
    aksi: str | None = Query(default=None, description="Saring satu nama tindakan"),
    actor_id: int | None = Query(default=None, description="Saring satu pelaku"),
    entity_type: str | None = Query(default=None),
    entity_id: str | None = Query(default=None),
    sejak: datetime | None = Query(default=None, description="Batas awal waktu"),
    sampai: datetime | None = Query(default=None, description="Batas akhir waktu"),
    batas: int = Query(default=50, ge=1, le=BATAS_MAKS),
    offset: int = Query(default=0, ge=0),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Daftar jejak audit terbaru lebih dulu, dengan penyaring opsional."""
    saringan = []
    if aksi:
        saringan.append(AuditLog.action == aksi)
    if actor_id is not None:
        saringan.append(AuditLog.actor_id == actor_id)
    if entity_type:
        saringan.append(AuditLog.entity_type == entity_type)
    if entity_id:
        saringan.append(AuditLog.entity_id == str(entity_id))
    if sejak:
        saringan.append(AuditLog.created_at >= sejak)
    if sampai:
        saringan.append(AuditLog.created_at <= sampai)

    jumlah = await db.scalar(
        select(func.count()).select_from(AuditLog).where(*saringan)
    )
    hasil = await db.execute(
        select(AuditLog)
        .where(*saringan)
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .limit(batas)
        .offset(offset)
    )
    baris = hasil.scalars().all()

    return AuditListResponse(
        total=int(jumlah or 0),
        items=[AuditEntry.model_validate(b) for b in baris],
        actions=AKSI,
    )
