"""drop lead_prospects.inteligencia_comercial

Revision ID: 56d39be2c889
Revises: f558023d5e5f
Create Date: 2026-08-22 00:00:00.000000

Inteligência Comercial saiu da Pesquisa de Leads (decisão travada nº 3, ver
docs/PLANO_SDR_AUTONOMO.md): agora é o SDR Argos, estritamente pós-promoção, gerando
direto em companies.inteligencia_comercial (coluna que já existe, ver fb11856ce211).
O endpoint POST/PATCH /lead-prospects/{id}/inteligencia-comercial foi removido — nada
mais escreve nesta coluna.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '56d39be2c889'
down_revision: Union[str, None] = 'f558023d5e5f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column('lead_prospects', 'inteligencia_comercial')


def downgrade() -> None:
    op.add_column('lead_prospects', sa.Column('inteligencia_comercial', sa.Text(), nullable=True))
