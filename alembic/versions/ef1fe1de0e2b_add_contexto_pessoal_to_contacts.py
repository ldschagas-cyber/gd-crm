"""add contexto_pessoal to contacts

Revision ID: ef1fe1de0e2b
Revises: 4b65d73c6432
Create Date: 2026-08-03 20:49:44.049876
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'ef1fe1de0e2b'
down_revision: Union[str, None] = '4b65d73c6432'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('contacts', sa.Column('contexto_pessoal', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('contacts', 'contexto_pessoal')
