"""add origem_options

Revision ID: a13252c10851
Revises: f3a7c9d2e5b1
Create Date: 2026-08-11 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a13252c10851'
down_revision: Union[str, None] = 'f3a7c9d2e5b1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('origem_options',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('nome', sa.String(length=80), nullable=False),
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('tenant_id', 'nome', name='uq_origem_option_tenant_nome')
    )
    op.create_index(op.f('ix_origem_options_tenant_id'), 'origem_options', ['tenant_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_origem_options_tenant_id'), table_name='origem_options')
    op.drop_table('origem_options')
