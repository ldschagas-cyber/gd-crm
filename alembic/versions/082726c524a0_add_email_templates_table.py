"""add email_templates table

Revision ID: 082726c524a0
Revises: b3f7a1c9d2e4
Create Date: 2026-07-29 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = '082726c524a0'
down_revision: Union[str, None] = 'b3f7a1c9d2e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('email_templates',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('nome', sa.String(length=120), nullable=False),
    sa.Column('assunto', sa.String(length=255), nullable=False),
    sa.Column('corpo', sa.Text(), nullable=False),
    sa.Column('variaveis_disponiveis', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
    sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_email_templates_tenant_id'), 'email_templates', ['tenant_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_email_templates_tenant_id'), table_name='email_templates')
    op.drop_table('email_templates')
