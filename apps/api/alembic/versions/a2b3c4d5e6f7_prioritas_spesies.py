"""prioritas dan sumber_prioritas pada species

Revision ID: a2b3c4d5e6f7
Revises: f1c2d3e4a5b6
Create Date: 2026-10-05

Menambah kolom prioritas (bool) dan sumber_prioritas (iucn, permen_p106, admin,
atau kosong) untuk menandai spesies prioritas konservasi.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'a2b3c4d5e6f7'
down_revision: str | None = 'f1c2d3e4a5b6'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'species',
        sa.Column('prioritas', sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column('species', sa.Column('sumber_prioritas', sa.String(length=20), nullable=True))


def downgrade() -> None:
    op.drop_column('species', 'sumber_prioritas')
    op.drop_column('species', 'prioritas')
