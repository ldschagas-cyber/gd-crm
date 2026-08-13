"""merge heads (responsavel_id contacts + whatsapp_content_sid)

Revision ID: b3d0a0f08570
Revises: f4a7c1d9b3e6, f7a2c8e4b1d6
Create Date: 2026-08-13 16:45:57.330921
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b3d0a0f08570'
down_revision: Union[str, None] = ('f4a7c1d9b3e6', 'f7a2c8e4b1d6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
