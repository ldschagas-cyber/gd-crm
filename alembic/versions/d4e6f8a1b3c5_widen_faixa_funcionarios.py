"""widen faixa_funcionarios on lead_prospects

Revision ID: d4e6f8a1b3c5
Revises: 7c1f4a92e6d3
Create Date: 2026-07-30 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd4e6f8a1b3c5'
down_revision: Union[str, None] = '7c1f4a92e6d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('lead_prospects', 'faixa_funcionarios', type_=sa.String(length=50))


def downgrade() -> None:
    op.alter_column('lead_prospects', 'faixa_funcionarios', type_=sa.String(length=20))
