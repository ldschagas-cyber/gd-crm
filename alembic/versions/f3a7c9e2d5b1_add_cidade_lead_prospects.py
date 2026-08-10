"""add cidade to lead_prospects

Revision ID: f3a7c9e2d5b1
Revises: e2f5b8c1a9d4
Create Date: 2026-08-10 14:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f3a7c9e2d5b1'
down_revision: Union[str, None] = 'e2f5b8c1a9d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Cidade da empresa pesquisada — antes só havia uf/regiao em lead_prospects, mas
    # Company já tem cidade (é inclusive coluna obrigatória na importação de empresas,
    # ver COMPANY_REQUIRED em app/workers/tasks.py). Copiado para Company.cidade na
    # promoção, igual aos demais campos de d8e1a4f0b6c3/e2f5b8c1a9d4.
    op.add_column('lead_prospects', sa.Column('cidade', sa.String(length=120), nullable=True))


def downgrade() -> None:
    op.drop_column('lead_prospects', 'cidade')
