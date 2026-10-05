"""fase 2: perangkat, unggah batch, progres job, kolom lokalisasi

Revision ID: b5a1c7d9e2f4
Revises: 9c1d2e3f4a5b
Create Date: 2026-09-21

Menambah kolom yang dipakai kontrak Fase 2. Tiga kolom di luar daftar kontrak
ikut ditambahkan karena endpoint yang diwajibkan kontrak tidak bisa mengisi
jawabannya tanpa kolom itu:

- `recordings.original_filename`: GET /api/v1/batches/{id} wajib menyebut nama
  berkas asli, sedangkan storage_key memakai nama acak supaya tidak bentrok.
- `users.name` dan `users.is_active`: GET /api/v1/users wajib mengembalikan
  keduanya. `name` diisi dari bagian sebelum tanda @ pada email yang sudah ada,
  bukan dikarang di lapisan API.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'b5a1c7d9e2f4'
down_revision: str | None = '9c1d2e3f4a5b'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'jobs', sa.Column('progress', sa.Integer(), nullable=False, server_default='0')
    )
    op.add_column('jobs', sa.Column('stage', sa.String(length=50), nullable=True))

    op.add_column('recordings', sa.Column('batch_id', sa.String(length=64), nullable=True))
    op.add_column(
        'recordings', sa.Column('original_filename', sa.String(length=255), nullable=True)
    )
    op.create_index('ix_recordings_batch_id', 'recordings', ['batch_id'])

    op.add_column('detections', sa.Column('azimuth_deg', sa.Float(), nullable=True))
    op.add_column('detections', sa.Column('azimuth_confidence', sa.Float(), nullable=True))
    op.add_column('detections', sa.Column('range_m', sa.Float(), nullable=True))
    op.add_column(
        'detections', sa.Column('localization_engine', sa.String(length=50), nullable=True)
    )

    op.add_column('devices', sa.Column('serial', sa.String(length=120), nullable=True))
    op.add_column(
        'devices',
        sa.Column('channel_count', sa.Integer(), nullable=False, server_default='1'),
    )
    op.add_column('devices', sa.Column('mic_spacing_m', sa.Float(), nullable=True))
    op.add_column('devices', sa.Column('reference_distance_m', sa.Float(), nullable=True))
    op.add_column('devices', sa.Column('reference_level_db', sa.Float(), nullable=True))
    op.add_column(
        'devices', sa.Column('installed_at', sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        'devices', sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.text('true'))
    )
    op.add_column('devices', sa.Column('notes', sa.Text(), nullable=True))

    op.add_column(
        'species',
        sa.Column('model_supported', sa.Boolean(), nullable=False, server_default=sa.text('false')),
    )

    op.add_column('users', sa.Column('name', sa.String(length=255), nullable=True))
    op.add_column(
        'users',
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
    )
    op.execute(
        "UPDATE users SET name = initcap(split_part(email, '@', 1)) WHERE name IS NULL"
    )


def downgrade() -> None:
    op.drop_column('users', 'is_active')
    op.drop_column('users', 'name')

    op.drop_column('species', 'model_supported')

    op.drop_column('devices', 'notes')
    op.drop_column('devices', 'active')
    op.drop_column('devices', 'installed_at')
    op.drop_column('devices', 'reference_level_db')
    op.drop_column('devices', 'reference_distance_m')
    op.drop_column('devices', 'mic_spacing_m')
    op.drop_column('devices', 'channel_count')
    op.drop_column('devices', 'serial')

    op.drop_column('detections', 'localization_engine')
    op.drop_column('detections', 'range_m')
    op.drop_column('detections', 'azimuth_confidence')
    op.drop_column('detections', 'azimuth_deg')

    op.drop_index('ix_recordings_batch_id', table_name='recordings')
    op.drop_column('recordings', 'original_filename')
    op.drop_column('recordings', 'batch_id')

    op.drop_column('jobs', 'stage')
    op.drop_column('jobs', 'progress')
