"""add workflows tables

Revision ID: 3538eb5dcd60
Revises: e35b87e52831
Create Date: 2026-07-29 03:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = '3538eb5dcd60'
down_revision: Union[str, None] = 'e35b87e52831'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('workflows',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('nome', sa.String(length=120), nullable=False),
    sa.Column('gatilho', sa.String(length=40), nullable=False),
    sa.Column('condicoes', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('ativo', sa.Boolean(), nullable=False),
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
    sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_workflows_tenant_id'), 'workflows', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_workflows_gatilho'), 'workflows', ['gatilho'], unique=False)

    op.create_table('workflow_actions',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('workflow_id', sa.UUID(), nullable=False),
    sa.Column('ordem', sa.Integer(), nullable=False),
    sa.Column('tipo_acao', sa.String(length=40), nullable=False),
    sa.Column('parametros', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.ForeignKeyConstraint(['workflow_id'], ['workflows.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_workflow_actions_workflow_id'), 'workflow_actions', ['workflow_id'], unique=False)

    op.create_table('workflow_execution_logs',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('workflow_id', sa.UUID(), nullable=True),
    sa.Column('workflow_nome', sa.String(length=120), nullable=False),
    sa.Column('entidade_ref', sa.UUID(), nullable=False),
    sa.Column('resultado', sa.String(length=20), nullable=False),
    sa.Column('detalhes', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('executado_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['workflow_id'], ['workflows.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
    sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_workflow_execution_logs_tenant_id'), 'workflow_execution_logs', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_workflow_execution_logs_workflow_id'), 'workflow_execution_logs', ['workflow_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_workflow_execution_logs_workflow_id'), table_name='workflow_execution_logs')
    op.drop_index(op.f('ix_workflow_execution_logs_tenant_id'), table_name='workflow_execution_logs')
    op.drop_table('workflow_execution_logs')
    op.drop_index(op.f('ix_workflow_actions_workflow_id'), table_name='workflow_actions')
    op.drop_table('workflow_actions')
    op.drop_index(op.f('ix_workflows_gatilho'), table_name='workflows')
    op.drop_index(op.f('ix_workflows_tenant_id'), table_name='workflows')
    op.drop_table('workflows')
