"""fase 2 lanjutan: arah kembar pada deteksi

Revision ID: c73f0a1b2d45
Revises: b5a1c7d9e2f4
Create Date: 2026-09-21

Susunan mikrofon segaris menghasilkan pola selisih waktu yang sama untuk sudut
cerminnya, misalnya 60 derajat dan 300 derajat. Keduanya sama sah, dan itu batas
susunan mikrofonya, bukan keraguan pengukuran. Kolom ini menyimpan sudut kembar
itu supaya satu arah tidak dilaporkan sebagai satu-satunya kemungkinan.

Dulu angka itu diringkas jadi keyakinan mendekati nol tanpa penjelasan, dan
pembaca mengira pengukurannya gagal.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'c73f0a1b2d45'
down_revision: str | None = 'b5a1c7d9e2f4'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'detections', sa.Column('azimuth_kembar_deg', sa.Float(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('detections', 'azimuth_kembar_deg')
