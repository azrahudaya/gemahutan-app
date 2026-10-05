"""khusus_tamu pada lokasi

Revision ID: f1c2d3e4a5b6
Revises: e1a7c3d54f28
Create Date: 2026-10-05

Menambah kolom khusus_tamu pada sites untuk menandai satu lokasi sistem yang
dipakai halaman depan "Coba contoh". Lokasi ini hanya terlihat akun tamu, dan
tidak terlihat peran petugas (admin, peneliti, ranger).
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'f1c2d3e4a5b6'
down_revision: str | None = 'e1a7c3d54f28'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'sites',
        sa.Column('khusus_tamu', sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column('sites', 'khusus_tamu')
