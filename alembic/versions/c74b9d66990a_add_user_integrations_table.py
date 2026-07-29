"""add user_integrations table

Revision ID: c74b9d66990a
Revises: d224b580a440
Create Date: 2026-07-28 16:22:31.276450
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c74b9d66990a'
down_revision: Union[str, None] = 'd224b580a440'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('user_integrations',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('provider', sa.String(length=20), nullable=False),
    sa.Column('tipo', sa.String(length=20), nullable=False),
    sa.Column('access_token_enc', sa.Text(), nullable=True),
    sa.Column('refresh_token_enc', sa.Text(), nullable=True),
    sa.Column('conectado_em', sa.DateTime(timezone=True), nullable=True),
    sa.Column('ativo', sa.Boolean(), nullable=False),
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'tipo', name='uq_user_integration_user_tipo')
    )
    op.create_index(op.f('ix_user_integrations_tenant_id'), 'user_integrations', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_user_integrations_user_id'), 'user_integrations', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_user_integrations_user_id'), table_name='user_integrations')
    op.drop_index(op.f('ix_user_integrations_tenant_id'), table_name='user_integrations')
    op.drop_table('user_integrations')
