"""add email to lead_prospects

Revision ID: e2f5b8c1a9d4
Revises: d8e1a4f0b6c3
Create Date: 2026-08-10 10:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e2f5b8c1a9d4'
down_revision: Union[str, None] = 'd8e1a4f0b6c3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # E-mail geral/institucional da empresa pesquisada — mesmo padrão de linkedin/
    # contato_sugerido (ver d8e1a4f0b6c3): capturado na Pesquisa de Leads e copiado
    # para Company.email na promoção, em vez de ficar só disponível via importação.
    op.add_column('lead_prospects', sa.Column('email', sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column('lead_prospects', 'email')
