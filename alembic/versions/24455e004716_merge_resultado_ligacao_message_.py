"""merge resultado_ligacao message_templates

Revision ID: 24455e004716
Revises: 829cf6eb9b04, c4d8e2a7f159
Create Date: 2026-08-10 16:17:24.639923
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '24455e004716'
down_revision: Union[str, None] = ('829cf6eb9b04', 'c4d8e2a7f159')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
