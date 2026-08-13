"""add customer success (cs_fase, health score, onboarding, assinatura renovacao, deal tipo)

Revision ID: a0694c4c25bb
Revises: a1c4e8f2b6d9
Create Date: 2026-08-13 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'a0694c4c25bb'
# f7a2c8e4b1d6 (não a1c4e8f2b6d9 diretamente) — já era a ponta real da cadeia neste
# branch antes desta migração (feat/whatsapp-content-sid, commit cafdbd7), encadeado
# a partir do mesmo a1c4e8f2b6d9. Não toca nenhuma tabela em comum.
down_revision: Union[str, None] = 'f7a2c8e4b1d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Customer Success (ver docs/PLANO_CUSTOMER_SUCCESS.md) — tudo aditivo, sem
    # backfill retroativo por inferência: colunas nascem NULL pra toda empresa/
    # assinatura já existente, mesmo padrão de `funil_estagio` (Central de Leads).

    # ---- companies: fase de Customer Success ------------------------------------
    op.add_column('companies', sa.Column('cs_fase', sa.String(length=20), nullable=True))
    op.add_column('companies', sa.Column('cs_fase_atualizada_em', sa.DateTime(timezone=True), nullable=True))
    op.add_column('companies', sa.Column('cs_responsavel_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('companies', sa.Column('health_score', sa.Integer(), nullable=True))
    op.add_column('companies', sa.Column('health_score_atualizado_em', sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f('ix_companies_cs_fase'), 'companies', ['cs_fase'], unique=False)
    op.create_foreign_key(
        'fk_companies_cs_responsavel_id_users', 'companies', 'users', ['cs_responsavel_id'], ['id'],
    )

    # ---- assinaturas: prazo contratual real / renovação -------------------------
    op.add_column('assinaturas', sa.Column('ciclo_renovacao_meses', sa.Integer(), nullable=True))
    op.add_column('assinaturas', sa.Column('data_renovacao', sa.Date(), nullable=True))
    op.create_index(op.f('ix_assinaturas_data_renovacao'), 'assinaturas', ['data_renovacao'], unique=False)

    # ---- deals: distingue negócio novo de expansão/upsell -----------------------
    op.add_column(
        'deals', sa.Column('tipo', sa.String(length=20), nullable=False, server_default='novo_negocio'),
    )
    op.alter_column('deals', 'tipo', server_default=None)

    # ---- onboarding_checklist_items ----------------------------------------------
    op.create_table(
        'onboarding_checklist_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('companies.id'), nullable=False),
        sa.Column('titulo', sa.String(length=255), nullable=False),
        sa.Column('ordem', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pendente'),
        sa.Column('prazo', sa.Date(), nullable=True),
        sa.Column('concluido_em', sa.DateTime(timezone=True), nullable=True),
        sa.Column('responsavel_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.alter_column('onboarding_checklist_items', 'ordem', server_default=None)
    op.alter_column('onboarding_checklist_items', 'status', server_default=None)
    op.create_index('ix_onboarding_checklist_items_tenant_id', 'onboarding_checklist_items', ['tenant_id'])
    op.create_index('ix_onboarding_checklist_items_company_id', 'onboarding_checklist_items', ['company_id'])


def downgrade() -> None:
    op.drop_index('ix_onboarding_checklist_items_company_id', table_name='onboarding_checklist_items')
    op.drop_index('ix_onboarding_checklist_items_tenant_id', table_name='onboarding_checklist_items')
    op.drop_table('onboarding_checklist_items')

    op.drop_column('deals', 'tipo')

    op.drop_index(op.f('ix_assinaturas_data_renovacao'), table_name='assinaturas')
    op.drop_column('assinaturas', 'data_renovacao')
    op.drop_column('assinaturas', 'ciclo_renovacao_meses')

    op.drop_constraint('fk_companies_cs_responsavel_id_users', 'companies', type_='foreignkey')
    op.drop_index(op.f('ix_companies_cs_fase'), table_name='companies')
    op.drop_column('companies', 'health_score_atualizado_em')
    op.drop_column('companies', 'health_score')
    op.drop_column('companies', 'cs_responsavel_id')
    op.drop_column('companies', 'cs_fase_atualizada_em')
    op.drop_column('companies', 'cs_fase')
