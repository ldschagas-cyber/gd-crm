"""add sdr argos fields to companies

Revision ID: 27ebd1e9bdb4
Revises: d9e1f3a5c7b2
Create Date: 2026-08-21 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '27ebd1e9bdb4'
down_revision: Union[str, None] = 'd9e1f3a5c7b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # `inteligencia_comercial` já existe (fb11856ce211) e passa a ser gerada direto aqui
    # pelo SDR Argos, pós-promoção, em vez de copiada do lead (ver PLANO_SDR_AUTONOMO.md §0.5).
    op.add_column('companies', sa.Column('cadencia_sugerida', sa.Text(), nullable=True))
    op.add_column('companies', sa.Column('roteiro_ligacao', sa.Text(), nullable=True))
    op.add_column('companies', sa.Column('sdr_argos_atualizado_em', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('companies', 'sdr_argos_atualizado_em')
    op.drop_column('companies', 'roteiro_ligacao')
    op.drop_column('companies', 'cadencia_sugerida')
