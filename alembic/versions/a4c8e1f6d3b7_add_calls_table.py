"""add calls table

Revision ID: a4c8e1f6d3b7
Revises: 2f4b6d8e0a1c
Create Date: 2026-08-01 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a4c8e1f6d3b7'
down_revision: Union[str, None] = '2f4b6d8e0a1c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('calls',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('call_sid', sa.String(length=64), nullable=False),
    sa.Column('direcao', sa.String(length=10), nullable=False),
    sa.Column('de_numero', sa.String(length=20), nullable=True),
    sa.Column('para_numero', sa.String(length=20), nullable=True),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('duracao_segundos', sa.Integer(), nullable=True),
    sa.Column('finalizada_em', sa.DateTime(timezone=True), nullable=True),
    sa.Column('user_id', sa.UUID(), nullable=True),
    sa.Column('company_id', sa.UUID(), nullable=True),
    sa.Column('contact_id', sa.UUID(), nullable=True),
    sa.Column('deal_id', sa.UUID(), nullable=True),
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
    sa.ForeignKeyConstraint(['contact_id'], ['contacts.id'], ),
    sa.ForeignKeyConstraint(['deal_id'], ['deals.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('call_sid', name='uq_calls_call_sid'),
    )
    op.create_index(op.f('ix_calls_call_sid'), 'calls', ['call_sid'], unique=True)
    op.create_index(op.f('ix_calls_tenant_id'), 'calls', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_calls_user_id'), 'calls', ['user_id'], unique=False)
    op.create_index(op.f('ix_calls_company_id'), 'calls', ['company_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_calls_company_id'), table_name='calls')
    op.drop_index(op.f('ix_calls_user_id'), table_name='calls')
    op.drop_index(op.f('ix_calls_tenant_id'), table_name='calls')
    op.drop_index(op.f('ix_calls_call_sid'), table_name='calls')
    op.drop_table('calls')
