"""metas de venda (equipe/vendedor por mês) e metas de ligações por vendedor

Cria `teams` (equipe, com gestor) e `sales_targets` (meta de venda por vendedor
por mês — qtd e valor), liga o vendedor à equipe via `users.team_id`, e adiciona
`users.meta_ligacoes_semanal/mensal` (fixas, no molde de meta_pesquisa).

Revision ID: d9e1f3a5c7b2
Revises: e7b1c4a9f2d0
Create Date: 2026-08-20 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd9e1f3a5c7b2'
down_revision: Union[str, None] = 'e7b1c4a9f2d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'teams',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('nome', sa.String(length=120), nullable=False),
        sa.Column('gestor_id', sa.UUID(), nullable=True),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['gestor_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_teams_tenant_id'), 'teams', ['tenant_id'], unique=False)

    op.add_column('users', sa.Column('team_id', sa.UUID(), nullable=True))
    op.create_foreign_key('fk_users_team_id_teams', 'users', 'teams', ['team_id'], ['id'])
    op.create_index(op.f('ix_users_team_id'), 'users', ['team_id'], unique=False)

    op.add_column('users', sa.Column('meta_ligacoes_semanal', sa.Integer(), nullable=True))
    op.add_column('users', sa.Column('meta_ligacoes_mensal', sa.Integer(), nullable=True))

    op.create_table(
        'sales_targets',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('mes', sa.String(length=7), nullable=False),
        sa.Column('meta_qtd', sa.Integer(), nullable=True),
        sa.Column('meta_valor', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'user_id', 'mes', name='uq_sales_target_tenant_user_mes'),
    )
    op.create_index(op.f('ix_sales_targets_tenant_id'), 'sales_targets', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_sales_targets_user_id'), 'sales_targets', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_sales_targets_user_id'), table_name='sales_targets')
    op.drop_index(op.f('ix_sales_targets_tenant_id'), table_name='sales_targets')
    op.drop_table('sales_targets')

    op.drop_column('users', 'meta_ligacoes_mensal')
    op.drop_column('users', 'meta_ligacoes_semanal')

    op.drop_index(op.f('ix_users_team_id'), table_name='users')
    op.drop_constraint('fk_users_team_id_teams', 'users', type_='foreignkey')
    op.drop_column('users', 'team_id')

    op.drop_index(op.f('ix_teams_tenant_id'), table_name='teams')
    op.drop_table('teams')
