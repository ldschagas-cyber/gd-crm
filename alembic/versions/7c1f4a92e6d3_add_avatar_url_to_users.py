"""add avatar_url to users

Revision ID: 7c1f4a92e6d3
Revises: 3538eb5dcd60
Create Date: 2026-07-29 04:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '7c1f4a92e6d3'
down_revision: Union[str, None] = '3538eb5dcd60'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('avatar_url', sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'avatar_url')
