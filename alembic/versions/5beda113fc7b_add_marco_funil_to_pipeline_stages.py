"""add marco_funil to pipeline_stages

Revision ID: 5beda113fc7b
Revises: a8d4f1c6b3e9
Create Date: 2026-08-10 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '5beda113fc7b'
down_revision: Union[str, None] = 'a8d4f1c6b3e9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Metas do Funil (controle de fase por percentual, ver docs/PLANO_METAS_FUNIL.md) —
    # aponta qual etapa de um Pipeline corresponde a "Diagnóstico realizado" / "Proposta
    # enviada" no funil de metas, desacoplado do *nome* da etapa (livre, editável por
    # tenant). NULL para toda etapa existente: nenhuma é inferida por nome, é sempre
    # atribuição manual na configuração do Pipeline.
    op.add_column('pipeline_stages', sa.Column('marco_funil', sa.String(length=20), nullable=True))


def downgrade() -> None:
    op.drop_column('pipeline_stages', 'marco_funil')
