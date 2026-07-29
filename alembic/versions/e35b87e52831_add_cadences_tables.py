"""add cadences tables

Revision ID: e35b87e52831
Revises: 1091276b8ab5
Create Date: 2026-07-29 02:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e35b87e52831'
down_revision: Union[str, None] = '1091276b8ab5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('cadences',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('nome', sa.String(length=120), nullable=False),
    sa.Column('ativo', sa.Boolean(), nullable=False),
    sa.Column('pausar_em_resposta', sa.Boolean(), nullable=False),
    sa.Column('criar_followup', sa.Boolean(), nullable=False),
    sa.Column('followup_titulo', sa.String(length=255), nullable=True),
    sa.Column('created_by', sa.UUID(), nullable=False),
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
    sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_cadences_tenant_id'), 'cadences', ['tenant_id'], unique=False)

    op.create_table('cadence_steps',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('cadence_id', sa.UUID(), nullable=False),
    sa.Column('ordem', sa.Integer(), nullable=False),
    sa.Column('dias_espera', sa.Integer(), nullable=False),
    sa.Column('template_id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['cadence_id'], ['cadences.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['template_id'], ['email_templates.id'], ),
    sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_cadence_steps_cadence_id'), 'cadence_steps', ['cadence_id'], unique=False)

    op.create_table('cadence_enrollments',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('cadence_id', sa.UUID(), nullable=False),
    sa.Column('company_id', sa.UUID(), nullable=True),
    sa.Column('contact_id', sa.UUID(), nullable=True),
    sa.Column('deal_id', sa.UUID(), nullable=True),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('step_atual', sa.Integer(), nullable=False),
    sa.Column('pausado_motivo', sa.String(length=60), nullable=True),
    sa.Column('iniciado_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('atualizado_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['cadence_id'], ['cadences.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
    sa.ForeignKeyConstraint(['contact_id'], ['contacts.id'], ),
    sa.ForeignKeyConstraint(['deal_id'], ['deals.id'], ),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
    sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_cadence_enrollments_tenant_id'), 'cadence_enrollments', ['tenant_id'], unique=False)
    op.create_index(
        'ix_cadence_enrollments_tenant_status_step', 'cadence_enrollments',
        ['tenant_id', 'status', 'step_atual'], unique=False,
    )


def downgrade() -> None:
    op.drop_index('ix_cadence_enrollments_tenant_status_step', table_name='cadence_enrollments')
    op.drop_index(op.f('ix_cadence_enrollments_tenant_id'), table_name='cadence_enrollments')
    op.drop_table('cadence_enrollments')
    op.drop_index(op.f('ix_cadence_steps_cadence_id'), table_name='cadence_steps')
    op.drop_table('cadence_steps')
    op.drop_index(op.f('ix_cadences_tenant_id'), table_name='cadences')
    op.drop_table('cadences')
