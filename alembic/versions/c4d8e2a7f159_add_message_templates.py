"""add message_templates table and sequence_steps.message_template_id

Revision ID: c4d8e2a7f159
Revises: 5beda113fc7b
Create Date: 2026-08-10 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'c4d8e2a7f159'
down_revision: Union[str, None] = '5beda113fc7b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('message_templates',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('canal', sa.String(length=20), nullable=False),
    sa.Column('nome', sa.String(length=120), nullable=False),
    sa.Column('corpo', sa.Text(), nullable=False),
    sa.Column('variaveis_disponiveis', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
    sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_message_templates_tenant_id'), 'message_templates', ['tenant_id'], unique=False)

    # Coluna separada de `template_id` (que tem FK pra email_templates) — um
    # step de WhatsApp/LinkedIn referencia um MessageTemplate por aqui.
    op.add_column('sequence_steps', sa.Column('message_template_id', sa.UUID(), nullable=True))
    op.create_foreign_key(
        'fk_sequence_steps_message_template_id', 'sequence_steps', 'message_templates',
        ['message_template_id'], ['id'],
    )


def downgrade() -> None:
    op.drop_constraint('fk_sequence_steps_message_template_id', 'sequence_steps', type_='foreignkey')
    op.drop_column('sequence_steps', 'message_template_id')
    op.drop_index(op.f('ix_message_templates_tenant_id'), table_name='message_templates')
    op.drop_table('message_templates')
