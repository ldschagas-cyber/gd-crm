"""add campos_personalizados to forms

Revision ID: b3f7a1c9d2e4
Revises: a9bde3475de8
Create Date: 2026-07-28 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'b3f7a1c9d2e4'
down_revision: Union[str, None] = 'a9bde3475de8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'forms',
        sa.Column('campos_personalizados', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
    )
    op.alter_column('forms', 'campos_personalizados', server_default=None)


def downgrade() -> None:
    op.drop_column('forms', 'campos_personalizados')
