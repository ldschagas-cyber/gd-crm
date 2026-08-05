"""add inteligencia_comercial to lead_prospects and companies

Revision ID: fb11856ce211
Revises: 0c752492c1ab
Create Date: 2026-08-05 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'fb11856ce211'
down_revision: Union[str, None] = '0c752492c1ab'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('lead_prospects', sa.Column('inteligencia_comercial', sa.Text(), nullable=True))
    op.add_column('companies', sa.Column('inteligencia_comercial', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('companies', 'inteligencia_comercial')
    op.drop_column('lead_prospects', 'inteligencia_comercial')
