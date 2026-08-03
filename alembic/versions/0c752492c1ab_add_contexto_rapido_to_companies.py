"""add contexto_rapido to companies

Revision ID: 0c752492c1ab
Revises: ef1fe1de0e2b
Create Date: 2026-08-03 20:52:36.909071
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0c752492c1ab'
down_revision: Union[str, None] = 'ef1fe1de0e2b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('companies', sa.Column('contexto_rapido', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('companies', 'contexto_rapido')
