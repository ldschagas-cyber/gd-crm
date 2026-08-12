"""add sla comercial

Revision ID: d3f8a1c5e7b9
Revises: a13252c10851
Create Date: 2026-08-12 10:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd3f8a1c5e7b9'
down_revision: Union[str, None] = 'a13252c10851'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Desde quando `companies.status` está no valor atual — ver docs/PLANO_SLA_COMERCIAL.md.
    # NULL pra empresas que já existiam antes desta coluna (sem backfill por inferência).
    op.add_column('companies', sa.Column('status_atualizado_em', sa.DateTime(timezone=True), nullable=True))

    op.create_table('activity_sla_rules',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('nome', sa.String(length=120), nullable=False),
    sa.Column('gatilho_tipo', sa.String(length=20), nullable=False),
    sa.Column('gatilho_valor', sa.String(length=40), nullable=False),
    sa.Column('prazo_horas', sa.Integer(), nullable=False),
    sa.Column('tipo_atividade_esperado', sa.String(length=20), nullable=True),
    sa.Column('ativo', sa.Boolean(), nullable=False),
    sa.Column('ordem', sa.Integer(), nullable=False),
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
    sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_activity_sla_rules_tenant_id'), 'activity_sla_rules', ['tenant_id'], unique=False)

    op.create_table('activity_sla_milestone_hits',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('rule_id', sa.UUID(), nullable=False),
    sa.Column('company_id', sa.UUID(), nullable=False),
    sa.Column('disparado_em', sa.DateTime(timezone=True), nullable=False),
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
    sa.ForeignKeyConstraint(['rule_id'], ['activity_sla_rules.id'], ),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('rule_id', 'company_id', name='uq_sla_milestone_hit_rule_company'),
    )
    op.create_index(op.f('ix_activity_sla_milestone_hits_tenant_id'), 'activity_sla_milestone_hits',
                    ['tenant_id'], unique=False)
    op.create_index(op.f('ix_activity_sla_milestone_hits_rule_id'), 'activity_sla_milestone_hits',
                    ['rule_id'], unique=False)
    op.create_index(op.f('ix_activity_sla_milestone_hits_company_id'), 'activity_sla_milestone_hits',
                    ['company_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_activity_sla_milestone_hits_company_id'), table_name='activity_sla_milestone_hits')
    op.drop_index(op.f('ix_activity_sla_milestone_hits_rule_id'), table_name='activity_sla_milestone_hits')
    op.drop_index(op.f('ix_activity_sla_milestone_hits_tenant_id'), table_name='activity_sla_milestone_hits')
    op.drop_table('activity_sla_milestone_hits')
    op.drop_index(op.f('ix_activity_sla_rules_tenant_id'), table_name='activity_sla_rules')
    op.drop_table('activity_sla_rules')
    op.drop_column('companies', 'status_atualizado_em')
