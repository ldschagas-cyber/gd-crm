"""add faixa_faturamento to companies

Revision ID: a8d4f1c6b3e9
Revises: f3a7c9e2d5b1
Create Date: 2026-08-10 16:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a8d4f1c6b3e9'
down_revision: Union[str, None] = 'f3a7c9e2d5b1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Faixa de faturamento (texto, ex.: "R$ 25–100 milhões") da Pesquisa de Leads — antes
    # promote() descartava esse dado por não ter onde colocá-lo sem inventar um número
    # exato em faturamento_estimado. Agora vira tag na ficha, igual ao que já acontece
    # com faixa_funcionarios em `porte`.
    op.add_column('companies', sa.Column('faixa_faturamento', sa.String(length=60), nullable=True))


def downgrade() -> None:
    op.drop_column('companies', 'faixa_faturamento')
