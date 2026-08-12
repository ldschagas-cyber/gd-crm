"""merge revenue_investments sla_comercial

Revision ID: 5261237b4c9f
Revises: ae62c7f90abd, d3f8a1c5e7b9
Create Date: 2026-08-12 16:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '5261237b4c9f'
down_revision: Union[str, None] = ('ae62c7f90abd', 'd3f8a1c5e7b9')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
