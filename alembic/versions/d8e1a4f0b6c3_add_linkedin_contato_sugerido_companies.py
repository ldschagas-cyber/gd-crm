"""add linkedin and contato_sugerido to companies

Revision ID: d8e1a4f0b6c3
Revises: c1a2b4d6e8f0
Create Date: 2026-08-09 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd8e1a4f0b6c3'
down_revision: Union[str, None] = 'c1a2b4d6e8f0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Bug: promoção de Pesquisa de Leads (LeadProspectService.promote()) descartava
    # linkedin e contato_sugerido do lead porque Company não tinha coluna pra receber
    # esses campos — dado preenchido na pesquisa sumia silenciosamente ao virar empresa.
    op.add_column('companies', sa.Column('linkedin', sa.String(length=255), nullable=True))
    op.add_column('companies', sa.Column('contato_sugerido', sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column('companies', 'contato_sugerido')
    op.drop_column('companies', 'linkedin')
