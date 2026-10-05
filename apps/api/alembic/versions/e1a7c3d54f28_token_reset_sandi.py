"""tabel token atur ulang sandi

Revision ID: e1a7c3d54f28
Revises: d8e4f2a91b07
Create Date: 2026-09-24

Sebelum ini satu-satunya jalan memulihkan akun adalah lewat SQL langsung, dan
itu tidak bisa dipakai di produksi.

Yang disimpan adalah hash token, bukan tokennya, dengan alasan yang sama seperti
sandi: kalau isi tabel ini bocor, token mentahnya tidak bisa dipakai membajak
akun. Barisnya juga tidak dihapus setelah dipakai, hanya ditandai `used_at`,
supaya jejak token yang pernah dipakai masih bisa ditelusuri.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'e1a7c3d54f28'
down_revision: str | None = 'd8e4f2a91b07'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Nomor versi token: naik saat sandi diatur ulang, dan token dengan versi lama
    # ditolak. Dipilih ketimbang kolom waktu karena iat pada JWT hanya bersatuan
    # detik, sehingga perbandingan waktu memaksa adanya toleransi.
    op.add_column(
        'users',
        sa.Column('token_version', sa.Integer(), nullable=False, server_default='0'),
    )

    op.create_table(
        'password_reset_tokens',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column(
            'user_id',
            sa.Integer(),
            sa.ForeignKey('users.id', ondelete='CASCADE'),
            nullable=False,
        ),
        # SHA-256 heksadesimal selalu 64 karakter, jadi lebarnya pasti.
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('requested_ip', sa.String(length=60), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index('ix_password_reset_tokens_user_id', 'password_reset_tokens', ['user_id'])
    op.create_index(
        'ix_password_reset_tokens_token_hash', 'password_reset_tokens', ['token_hash'], unique=True
    )


def downgrade() -> None:
    op.drop_index('ix_password_reset_tokens_token_hash', table_name='password_reset_tokens')
    op.drop_index('ix_password_reset_tokens_user_id', table_name='password_reset_tokens')
    op.drop_table('password_reset_tokens')
    op.drop_column('users', 'token_version')
