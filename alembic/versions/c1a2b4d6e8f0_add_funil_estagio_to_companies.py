"""add funil_estagio to companies

Revision ID: c1a2b4d6e8f0
Revises: 3409dad36252
Create Date: 2026-08-06 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c1a2b4d6e8f0'
down_revision: Union[str, None] = '3409dad36252'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Central de Leads — funil comercial pós-promoção (novo → qualificando → cadência →
    # mql → sql → convertido). Nasce NULL pra tudo que já existe: nenhuma empresa antiga é
    # inferida retroativamente, só passa a ter estágio quem entrar no funil dali pra frente
    # (promoção de lead, ou atribuição manual). Ver docs/PLANO_CENTRAL_DE_LEADS.md.
    op.add_column('companies', sa.Column('funil_estagio', sa.String(length=20), nullable=True))
    op.add_column('companies', sa.Column('funil_estagio_atualizado_em', sa.DateTime(timezone=True), nullable=True))
    op.create_index('ix_companies_funil_estagio', 'companies', ['funil_estagio'])


def downgrade() -> None:
    op.drop_index('ix_companies_funil_estagio', table_name='companies')
    op.drop_column('companies', 'funil_estagio_atualizado_em')
    op.drop_column('companies', 'funil_estagio')
