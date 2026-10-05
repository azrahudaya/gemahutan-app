"""tabel jejak audit

Revision ID: d8e4f2a91b07
Revises: c73f0a1b2d45
Create Date: 2026-09-24

Aplikasi ini memutuskan verifikasi deteksi, mengubah peran pengguna, dan
mengubah ambang model, tetapi tidak meninggalkan jejak siapa yang melakukannya
dan kapan. Tabel ini menutup celah itu.

Dua pilihan yang sengaja:

- `actor_id` TIDAK memakai ondelete cascade. Jejak audit justru paling perlu
  dibaca saat akunnya bermasalah atau dihapus, jadi barisnya tidak boleh ikut
  terhapus. `actor_email` disalin supaya barisnya tetap terbaca.
- `detail` bertipe JSONB, sehingga bentuk tiap tindakan boleh berbeda tanpa
  menambah kolom, dan tetap bisa dicari dengan operator JSON Postgres.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = 'd8e4f2a91b07'
down_revision: str | None = 'c73f0a1b2d45'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column(
            'actor_id',
            sa.Integer(),
            sa.ForeignKey('users.id', ondelete='SET NULL'),
            nullable=True,
        ),
        sa.Column('actor_email', sa.String(length=255), nullable=True),
        sa.Column('action', sa.String(length=60), nullable=False),
        sa.Column('entity_type', sa.String(length=40), nullable=True),
        sa.Column('entity_id', sa.String(length=60), nullable=True),
        sa.Column('detail', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('ip', sa.String(length=60), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index('ix_audit_logs_actor_id', 'audit_logs', ['actor_id'])
    op.create_index('ix_audit_logs_action', 'audit_logs', ['action'])
    op.create_index('ix_audit_logs_created_at', 'audit_logs', ['created_at'])
    op.create_index('ix_audit_logs_entity', 'audit_logs', ['entity_type', 'entity_id'])


def downgrade() -> None:
    op.drop_index('ix_audit_logs_entity', table_name='audit_logs')
    op.drop_index('ix_audit_logs_created_at', table_name='audit_logs')
    op.drop_index('ix_audit_logs_action', table_name='audit_logs')
    op.drop_index('ix_audit_logs_actor_id', table_name='audit_logs')
    op.drop_table('audit_logs')
