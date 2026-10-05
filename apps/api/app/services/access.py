"""Object-level access rules for the single-organization deployment.

Admins and researchers can review the organization's data. Rangers can read
only recordings they uploaded and data derived from those recordings. Site
metadata remains shared so a ranger can select an approved monitoring site
when uploading, but aggregate counts are scoped where the endpoint exposes
recording-derived data.
"""
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.sql import ColumnElement

from app.models.tables import Recording, User, UserRole
from app.services.tamu import DOMAIN_TAMU


def can_review_all(user: User) -> bool:
    return user.role in (UserRole.admin, UserRole.researcher)


def _bukan_tamu() -> ColumnElement[bool]:
    """Predikat SQL: rekaman yang bukan milik akun tamu.

    Data unggahan akun tamu halaman depan tidak boleh masuk data kawasan, jadi
    admin dan peneliti tidak melihat rekaman milik akun bertanda domain
    `@tamu.gemahutan.invalid` di daftar, statistik, laporan, atau ekspor.
    """
    guest_q = select(User.id).where(User.email.like(f"%@{DOMAIN_TAMU}"))
    return Recording.uploaded_by.not_in(guest_q)


def recording_scope(user: User) -> ColumnElement[bool]:
    """Return the SQL predicate for recordings visible to ``user``."""
    if can_review_all(user):
        return _bukan_tamu()
    return Recording.uploaded_by == user.id


def job_scope(user: User) -> ColumnElement[bool]:
    """Return the SQL predicate for jobs joined to their recording."""
    if can_review_all(user):
        return _bukan_tamu()
    return Recording.uploaded_by == user.id


def require_recording_access(recording: Recording | None, user: User) -> Recording:
    """Return a recording or hide an inaccessible object as HTTP 404."""
    if recording is None or (not can_review_all(user) and recording.uploaded_by != user.id):
        raise HTTPException(404, "Rekaman tidak ditemukan")
    return recording


def visible_recording_ids(user: User):
    """Subquery used when a route starts from Detection, Job, or an aggregate."""
    query = select(Recording.id)
    if can_review_all(user):
        query = query.where(_bukan_tamu())
    else:
        query = query.where(Recording.uploaded_by == user.id)
    return query


async def site_ids_prioritas(db) -> set[int]:
    """Id lokasi yang punya deteksi spesies prioritas.

    Lokasi ini dirahasiakan untuk peran selain admin dan peneliti: koordinatnya
    dibulatkan dan diberi tanda lokasi_disamarkan.
    """
    from app.models.tables import Detection, Species

    result = await db.execute(
        select(Recording.site_id)
        .join(Detection, Detection.recording_id == Recording.id)
        .join(Species, Species.id == Detection.species_id)
        .where(Species.prioritas.is_(True))
        .distinct()
    )
    return {int(r[0]) for r in result.all()}
