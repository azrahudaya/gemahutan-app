"""site details: location, elevation, description, notes

Revision ID: 9c1d2e3f4a5b
Revises: 97f165231400
Create Date: 2026-09-20

Menambah kolom yang dipakai form "Tambah Lokasi" di frontend supaya data yang
diisi pengguna benar-benar tersimpan, bukan dibuang diam-diam.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '9c1d2e3f4a5b'
down_revision: str | None = '97f165231400'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('sites', sa.Column('location', sa.String(length=255), nullable=True))
    op.add_column('sites', sa.Column('elevation_m', sa.Float(), nullable=True))
    op.add_column('sites', sa.Column('description', sa.Text(), nullable=True))
    op.add_column('sites', sa.Column('notes', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('sites', 'notes')
    op.drop_column('sites', 'description')
    op.drop_column('sites', 'elevation_m')
    op.drop_column('sites', 'location')
