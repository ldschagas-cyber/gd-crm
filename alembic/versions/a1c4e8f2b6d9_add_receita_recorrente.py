"""add receita recorrente (assinaturas, assinatura_eventos)

Revision ID: a1c4e8f2b6d9
Revises: 5261237b4c9f
Create Date: 2026-08-13 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'a1c4e8f2b6d9'
down_revision: Union[str, None] = '5261237b4c9f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Receita Recorrente (ver docs/PLANO_RECEITA_RECORRENTE.md) — duas tabelas novas,
    # aditivas, sem tocar em nenhum modelo existente. `assinaturas` guarda o estado atual;
    # `assinatura_eventos` é o livro-razão imutável de toda mudança de valor/status, usado
    # pelo RevenueService pra derivar MRR/ARR/Churn/Expansão/NRR por período (§2 do plano).
    op.create_table(
        'assinaturas',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('companies.id'), nullable=False),
        sa.Column('deal_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('deals.id'), nullable=True),
        sa.Column('nome_plano', sa.String(length=120), nullable=False),
        sa.Column('valor_mensal', sa.Numeric(15, 2), nullable=False),
        sa.Column('ciclo_cobranca', sa.String(length=10), nullable=False, server_default='mensal'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='ativa'),
        sa.Column('data_inicio', sa.Date(), nullable=False),
        sa.Column('data_cancelamento', sa.Date(), nullable=True),
        sa.Column('motivo_cancelamento', sa.String(length=255), nullable=True),
        sa.Column('responsavel_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_assinaturas_tenant_id', 'assinaturas', ['tenant_id'])
    op.create_index('ix_assinaturas_company_id', 'assinaturas', ['company_id'])
    op.create_index('ix_assinaturas_status', 'assinaturas', ['status'])
    op.create_index('ix_assinaturas_company_status', 'assinaturas', ['company_id', 'status'])
    op.alter_column('assinaturas', 'ciclo_cobranca', server_default=None)
    op.alter_column('assinaturas', 'status', server_default=None)

    op.create_table(
        'assinatura_eventos',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('assinatura_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('assinaturas.id'), nullable=False),
        sa.Column('tipo', sa.String(length=20), nullable=False),
        sa.Column('valor_anterior', sa.Numeric(15, 2), nullable=True),
        sa.Column('valor_novo', sa.Numeric(15, 2), nullable=True),
        sa.Column('delta_mrr', sa.Numeric(15, 2), nullable=False),
        sa.Column('data_evento', sa.Date(), nullable=False),
        sa.Column('observacao', sa.Text(), nullable=True),
        sa.Column('criado_por', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_assinatura_eventos_tenant_id', 'assinatura_eventos', ['tenant_id'])
    op.create_index('ix_assinatura_eventos_assinatura_id', 'assinatura_eventos', ['assinatura_id'])
    op.create_index('ix_assinatura_eventos_tipo', 'assinatura_eventos', ['tipo'])
    op.create_index('ix_assinatura_eventos_data_evento', 'assinatura_eventos', ['data_evento'])
    op.create_index(
        'ix_assinatura_eventos_assinatura_data', 'assinatura_eventos', ['assinatura_id', 'data_evento'],
    )


def downgrade() -> None:
    op.drop_index('ix_assinatura_eventos_assinatura_data', table_name='assinatura_eventos')
    op.drop_index('ix_assinatura_eventos_data_evento', table_name='assinatura_eventos')
    op.drop_index('ix_assinatura_eventos_tipo', table_name='assinatura_eventos')
    op.drop_index('ix_assinatura_eventos_assinatura_id', table_name='assinatura_eventos')
    op.drop_index('ix_assinatura_eventos_tenant_id', table_name='assinatura_eventos')
    op.drop_table('assinatura_eventos')

    op.drop_index('ix_assinaturas_company_status', table_name='assinaturas')
    op.drop_index('ix_assinaturas_status', table_name='assinaturas')
    op.drop_index('ix_assinaturas_company_id', table_name='assinaturas')
    op.drop_index('ix_assinaturas_tenant_id', table_name='assinaturas')
    op.drop_table('assinaturas')
