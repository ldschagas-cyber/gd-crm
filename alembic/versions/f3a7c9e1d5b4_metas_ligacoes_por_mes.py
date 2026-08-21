"""metas de ligações por mês (call_targets) + remove colunas fixas de users

Converte a meta de ligações de colunas fixas em users
(meta_ligacoes_semanal/mensal) para uma tabela por mês (call_targets), no mesmo
modelo do sales_targets — a meta passa a ser definida na tela Metas de Ligações,
por mês, e não mais no cadastro do usuário.

Revision ID: f3a7c9e1d5b4
Revises: d9e1f3a5c7b2
Create Date: 2026-08-21 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f3a7c9e1d5b4'
down_revision: Union[str, None] = 'd9e1f3a5c7b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'call_targets',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('mes', sa.String(length=7), nullable=False),
        sa.Column('meta_semanal', sa.Integer(), nullable=True),
        sa.Column('meta_mensal', sa.Integer(), nullable=True),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'user_id', 'mes', name='uq_call_target_tenant_user_mes'),
    )
    op.create_index(op.f('ix_call_targets_tenant_id'), 'call_targets', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_call_targets_user_id'), 'call_targets', ['user_id'], unique=False)

    # Meta de ligações agora é por mês (call_targets) — as colunas fixas saem.
    op.drop_column('users', 'meta_ligacoes_mensal')
    op.drop_column('users', 'meta_ligacoes_semanal')


def downgrade() -> None:
    op.add_column('users', sa.Column('meta_ligacoes_semanal', sa.Integer(), nullable=True))
    op.add_column('users', sa.Column('meta_ligacoes_mensal', sa.Integer(), nullable=True))

    op.drop_index(op.f('ix_call_targets_user_id'), table_name='call_targets')
    op.drop_index(op.f('ix_call_targets_tenant_id'), table_name='call_targets')
    op.drop_table('call_targets')
