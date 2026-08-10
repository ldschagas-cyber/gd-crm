"""merge funil_metas resultado_ligacao

Revision ID: 829cf6eb9b04
Revises: 5beda113fc7b, c2f7a4e8b1d3
Create Date: 2026-08-10 16:02:35.303590
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '829cf6eb9b04'
down_revision: Union[str, None] = ('5beda113fc7b', 'c2f7a4e8b1d3')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
