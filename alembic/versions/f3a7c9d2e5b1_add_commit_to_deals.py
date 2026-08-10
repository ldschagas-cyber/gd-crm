"""add commit to deals

Revision ID: f3a7c9d2e5b1
Revises: 24455e004716
Create Date: 2026-08-10 18:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f3a7c9d2e5b1'
down_revision: Union[str, None] = '24455e004716'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Previsão Comercial (ver docs/PLANO_PREVISAO_COMERCIAL.md) — sinalizador manual, por
    # negócio, de que o vendedor confirma o fechamento no mês previsto. Distinto da
    # probabilidade ponderada (que vem da etapa do pipeline). server_default 'false' preenche
    # as linhas existentes sem exigir backfill separado.
    op.add_column('deals', sa.Column('commit', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.alter_column('deals', 'commit', server_default=None)


def downgrade() -> None:
    op.drop_column('deals', 'commit')
