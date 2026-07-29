"""add sequences tables

Revision ID: 1091276b8ab5
Revises: 082726c524a0
Create Date: 2026-07-29 01:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '1091276b8ab5'
down_revision: Union[str, None] = '082726c524a0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('sequences',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('nome', sa.String(length=120), nullable=False),
    sa.Column('ativo', sa.Boolean(), nullable=False),
    sa.Column('pausar_em_resposta', sa.Boolean(), nullable=False),
    sa.Column('created_by', sa.UUID(), nullable=False),
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
    sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_sequences_tenant_id'), 'sequences', ['tenant_id'], unique=False)

    op.create_table('sequence_steps',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('sequence_id', sa.UUID(), nullable=False),
    sa.Column('ordem', sa.Integer(), nullable=False),
    sa.Column('dia_offset', sa.Integer(), nullable=False),
    sa.Column('tipo', sa.String(length=20), nullable=False),
    sa.Column('template_id', sa.UUID(), nullable=True),
    sa.Column('instrucoes', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['sequence_id'], ['sequences.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['template_id'], ['email_templates.id'], ),
    sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_sequence_steps_sequence_id'), 'sequence_steps', ['sequence_id'], unique=False)

    op.create_table('sequence_enrollments',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('sequence_id', sa.UUID(), nullable=False),
    sa.Column('company_id', sa.UUID(), nullable=True),
    sa.Column('contact_id', sa.UUID(), nullable=True),
    sa.Column('deal_id', sa.UUID(), nullable=True),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('step_atual', sa.Integer(), nullable=False),
    sa.Column('pausado_motivo', sa.String(length=60), nullable=True),
    sa.Column('iniciado_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('atualizado_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['sequence_id'], ['sequences.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
    sa.ForeignKeyConstraint(['contact_id'], ['contacts.id'], ),
    sa.ForeignKeyConstraint(['deal_id'], ['deals.id'], ),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
    sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_sequence_enrollments_tenant_id'), 'sequence_enrollments', ['tenant_id'], unique=False)
    op.create_index(
        'ix_sequence_enrollments_tenant_status_step', 'sequence_enrollments',
        ['tenant_id', 'status', 'step_atual'], unique=False,
    )


def downgrade() -> None:
    op.drop_index('ix_sequence_enrollments_tenant_status_step', table_name='sequence_enrollments')
    op.drop_index(op.f('ix_sequence_enrollments_tenant_id'), table_name='sequence_enrollments')
    op.drop_table('sequence_enrollments')
    op.drop_index(op.f('ix_sequence_steps_sequence_id'), table_name='sequence_steps')
    op.drop_table('sequence_steps')
    op.drop_index(op.f('ix_sequences_tenant_id'), table_name='sequences')
    op.drop_table('sequences')
