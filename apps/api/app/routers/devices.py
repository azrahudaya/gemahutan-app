"""Perangkat akuisisi suara: daftar, tambah, ubah, hapus.

Halaman Perangkat sebelumnya hanya bisa dibaca dari data seed, padahal perangkat
di lapangan dipasang, dipindah, dan diganti. Tulis hanya untuk admin. Daftar
perangkat dibaca peneliti dan admin; ranger tidak perlu melihat daftar perangkat.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete as sa_delete
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_user, get_db, require_admin, require_peneliti
from app.models.tables import Device, Recording, Site, User
from app.schemas.device import DeviceCreate, DevicePilihan, DeviceResponse, DeviceUpdate

router = APIRouter(prefix="/api/v1/devices", tags=["devices"])


def _to_response(device: Device, site_name: str | None, recording_count: int) -> DeviceResponse:
    return DeviceResponse(
        id=device.id,
        name=device.name,
        type=device.type.value,
        site_id=device.site_id,
        site_name=site_name,
        serial=device.serial,
        channel_count=device.channel_count,
        mic_spacing_m=device.mic_spacing_m,
        reference_distance_m=device.reference_distance_m,
        reference_level_db=device.reference_level_db,
        installed_at=device.installed_at.isoformat() if device.installed_at else None,
        active=device.active,
        notes=device.notes,
        recording_count=recording_count,
    )


_SELECT_PERANGKAT = (
    select(
        Device,
        Site.name.label("site_name"),
        func.count(Recording.id).label("recording_count"),
    )
    .join(Site, Site.id == Device.site_id)
    .outerjoin(Recording, Recording.device_id == Device.id)
    .group_by(Device.id, Site.name)
)


async def _ambil(db: AsyncSession, device_id: int) -> DeviceResponse:
    """Satu perangkat beserta nama lokasi dan jumlah rekamannya."""
    result = await db.execute(_SELECT_PERANGKAT.where(Device.id == device_id))
    row = result.first()
    if not row:
        raise HTTPException(404, "Perangkat tidak ditemukan")
    return _to_response(row[0], row.site_name, row.recording_count or 0)


async def _cek_lokasi(db: AsyncSession, site_id: int) -> None:
    ada = (await db.execute(select(Site.id).where(Site.id == site_id))).scalar()
    if not ada:
        raise HTTPException(400, f"Lokasi {site_id} tidak ada")


@router.get("", response_model=list[DeviceResponse])
async def list_devices(
    site_id: int | None = Query(None),
    active: bool | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_peneliti),
):
    query = _SELECT_PERANGKAT.order_by(Device.name)
    if site_id is not None:
        query = query.where(Device.site_id == site_id)
    if active is not None:
        query = query.where(Device.active.is_(active))

    rows = (await db.execute(query)).all()
    return [_to_response(row[0], row.site_name, row.recording_count or 0) for row in rows]


@router.get("/pilihan", response_model=list[DevicePilihan])
async def list_devices_pilihan(
    site_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Daftar perangkat aktif singkat untuk dipilih saat rekam atau unggah.

    Terbuka untuk semua peran petugas termasuk ranger, karena form rekam dan
    unggah butuh memilih perangkat. Kolom teknis (serial, jarak mikrofon,
    jumlah rekaman) tidak ikut, supaya data analitis tetap tertutup untuk ranger.
    """
    query = (
        select(Device, Site.name.label("site_name"))
        .join(Site, Site.id == Device.site_id)
        .where(Device.active.is_(True))
        .order_by(Device.name)
    )
    if site_id is not None:
        query = query.where(Device.site_id == site_id)

    rows = (await db.execute(query)).all()
    return [
        DevicePilihan(
            id=row[0].id,
            name=row[0].name,
            site_id=row[0].site_id,
            site_name=row.site_name,
            channel_count=row[0].channel_count,
            active=row[0].active,
        )
        for row in rows
    ]


@router.post("", response_model=DeviceResponse, status_code=201)
async def create_device(
    body: DeviceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    nama = body.name.strip()
    if not nama:
        raise HTTPException(400, "Nama perangkat wajib diisi")
    await _cek_lokasi(db, body.site_id)

    device = Device(
        name=nama,
        type=body.type,
        site_id=body.site_id,
        serial=body.serial,
        channel_count=body.channel_count,
        mic_spacing_m=body.mic_spacing_m,
        reference_distance_m=body.reference_distance_m,
        reference_level_db=body.reference_level_db,
        installed_at=body.installed_at,
        notes=body.notes,
    )
    db.add(device)
    await db.commit()
    return await _ambil(db, device.id)


@router.patch("/{device_id}", response_model=DeviceResponse)
async def update_device(
    device_id: int,
    body: DeviceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    result = await db.execute(select(Device).where(Device.id == device_id))
    device = result.scalar()
    if not device:
        raise HTTPException(404, "Perangkat tidak ditemukan")

    perubahan = body.model_dump(exclude_unset=True)
    if not perubahan:
        raise HTTPException(400, "Tidak ada kolom yang diubah")

    if "name" in perubahan:
        nama = (perubahan["name"] or "").strip()
        if not nama:
            raise HTTPException(400, "Nama perangkat wajib diisi")
        perubahan["name"] = nama
    if "site_id" in perubahan:
        await _cek_lokasi(db, perubahan["site_id"])

    for kolom, nilai in perubahan.items():
        setattr(device, kolom, nilai)

    await db.commit()
    return await _ambil(db, device_id)


@router.delete("/{device_id}", status_code=204)
async def delete_device(
    device_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Hapus perangkat. Ditolak kalau masih ada rekaman yang memakainya.

    Menghapus perangkat berisi rekaman akan menghapus jejak alat mana yang
    merekam, dan itu dipakai untuk menyaring serta menilai mutu data.
    """
    ada = (await db.execute(select(Device.id).where(Device.id == device_id))).scalar()
    if not ada:
        raise HTTPException(404, "Perangkat tidak ditemukan")

    jumlah = (
        await db.execute(
            select(func.count(Recording.id)).where(Recording.device_id == device_id)
        )
    ).scalar() or 0
    if jumlah:
        raise HTTPException(
            409,
            f"Perangkat ini masih dipakai {jumlah} rekaman. Pindahkan rekamannya dulu, lalu hapus.",
        )

    await db.execute(sa_delete(Device).where(Device.id == device_id))
    await db.commit()
