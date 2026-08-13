"""merge heads (customer success + responsavel_id/whatsapp)

Revision ID: 87bae0b12c44
Revises: a0694c4c25bb, b3d0a0f08570
Create Date: 2026-08-13 17:15:18.046551
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '87bae0b12c44'
down_revision: Union[str, None] = ('a0694c4c25bb', 'b3d0a0f08570')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
