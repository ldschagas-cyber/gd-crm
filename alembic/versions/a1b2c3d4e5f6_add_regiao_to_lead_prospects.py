"""add regiao to lead_prospects

Revision ID: a1b2c3d4e5f6
Revises: 6da712e0d874
Create Date: 2026-07-28 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '6da712e0d874'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('lead_prospects', sa.Column('regiao', sa.String(length=20), nullable=True))


def downgrade() -> None:
    op.drop_column('lead_prospects', 'regiao')
