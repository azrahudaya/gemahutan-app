"""Skema akun untuk halaman pengguna yang hanya bisa dibuka admin."""
from pydantic import BaseModel, EmailStr

from app.models.tables import UserRole


class UserListResponse(BaseModel):
    id: int
    email: str
    name: str | None = None
    role: str
    created_at: str
    is_active: bool
    recording_count: int = 0
    site_count: int = 0
    # Hanya diisi pada respons undangan. False berarti surel tidak terkirim dan
    # UI harus menampilkan peringatan, bukan klaim sukses.
    email_terkirim: bool | None = None


class RoleUpdate(BaseModel):
    role: UserRole


class InviteUserRequest(BaseModel):
    email: EmailStr
    name: str | None = None
    role: UserRole
