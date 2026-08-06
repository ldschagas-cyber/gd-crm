"""add descricao to tasks

Revision ID: a3f6c1d9e2b7
Revises: fb11856ce211
Create Date: 2026-08-05 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a3f6c1d9e2b7'
down_revision: Union[str, None] = 'fb11856ce211'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('tasks', sa.Column('descricao', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('tasks', 'descricao')
