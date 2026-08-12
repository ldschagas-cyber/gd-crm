"""add revenue_investments

Revision ID: b6d2a91f4c7e
Revises: f3a7c9d2e5b1
Create Date: 2026-08-12 15:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'b6d2a91f4c7e'
down_revision: Union[str, None] = 'f3a7c9d2e5b1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # CAC & ROI comercial (ver docs/PLANO_PREVISAO_COMERCIAL.md §8) — lançamento manual de
    # investimento por mês/categoria. Tabela nova, aditiva, sem tocar em nenhum modelo
    # existente; nenhuma outra parte do sistema grava custo/investimento hoje.
    op.create_table(
        'revenue_investments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('competencia', sa.Date(), nullable=False),
        sa.Column('categoria', sa.String(length=20), nullable=False, server_default='outros'),
        sa.Column('valor', sa.Numeric(15, 2), nullable=False),
        sa.Column('observacao', sa.String(length=255), nullable=True),
        sa.Column('criado_por', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_revenue_investments_tenant_id', 'revenue_investments', ['tenant_id'])
    op.create_index('ix_revenue_investments_competencia', 'revenue_investments', ['competencia'])
    op.alter_column('revenue_investments', 'categoria', server_default=None)


def downgrade() -> None:
    op.drop_index('ix_revenue_investments_competencia', table_name='revenue_investments')
    op.drop_index('ix_revenue_investments_tenant_id', table_name='revenue_investments')
    op.drop_table('revenue_investments')
