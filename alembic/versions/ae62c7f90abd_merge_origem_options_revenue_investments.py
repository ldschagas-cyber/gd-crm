"""merge origem_options revenue_investments

Revision ID: ae62c7f90abd
Revises: a13252c10851, b6d2a91f4c7e
Create Date: 2026-08-12 15:05:12.150126
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'ae62c7f90abd'
down_revision: Union[str, None] = ('a13252c10851', 'b6d2a91f4c7e')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
