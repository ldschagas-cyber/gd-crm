"""add cnae_codes

Revision ID: b7d2f9a4c6e8
Revises: d4e6f8a1b3c5
Create Date: 2026-07-30 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b7d2f9a4c6e8'
down_revision: Union[str, None] = 'd4e6f8a1b3c5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'cnae_codes',
        sa.Column('codigo', sa.String(length=7), primary_key=True),
        sa.Column('descricao', sa.String(length=255), nullable=False),
        sa.Column('secao', sa.String(length=1), nullable=False),
        sa.Column('divisao', sa.String(length=2), nullable=False),
        sa.Column('grupo', sa.String(length=3), nullable=False),
        sa.Column('classe', sa.String(length=5), nullable=False),
    )
    op.create_index('ix_cnae_codes_secao', 'cnae_codes', ['secao'])
    op.create_index('ix_cnae_codes_divisao', 'cnae_codes', ['divisao'])
    op.create_index('ix_cnae_codes_grupo', 'cnae_codes', ['grupo'])
    op.create_index('ix_cnae_codes_classe', 'cnae_codes', ['classe'])


def downgrade() -> None:
    op.drop_table('cnae_codes')
