"""add cor_exibicao to pipelines

Revision ID: d224b580a440
Revises: 0001_initial
Create Date: 2026-07-28 15:14:20.993112
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd224b580a440'
down_revision: Union[str, None] = '0001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'pipelines',
        sa.Column('cor_exibicao', sa.String(length=20), nullable=False, server_default='sem_cor'),
    )
    op.alter_column('pipelines', 'cor_exibicao', server_default=None)


def downgrade() -> None:
    op.drop_column('pipelines', 'cor_exibicao')
