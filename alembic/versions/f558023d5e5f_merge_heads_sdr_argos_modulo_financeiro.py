"""merge heads (sdr argos + modulo financeiro)

Revision ID: f558023d5e5f
Revises: 27ebd1e9bdb4, c4f7a2b9e1d3
Create Date: 2026-08-21 23:18:49.021243
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f558023d5e5f'
down_revision: Union[str, None] = ('27ebd1e9bdb4', 'c4f7a2b9e1d3')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
