"""add cnpj to lead_prospects

Revision ID: f1a3c5e7b9d2
Revises: b7d2f9a4c6e8
Create Date: 2026-07-30 00:00:01.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f1a3c5e7b9d2'
down_revision: Union[str, None] = 'b7d2f9a4c6e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('lead_prospects', sa.Column('cnpj', sa.String(length=14), nullable=True))


def downgrade() -> None:
    op.drop_column('lead_prospects', 'cnpj')
