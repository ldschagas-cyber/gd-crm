"""add dossie fields to companies

Revision ID: 2f4b6d8e0a1c
Revises: f1a3c5e7b9d2
Create Date: 2026-07-30 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '2f4b6d8e0a1c'
down_revision: Union[str, None] = 'f1a3c5e7b9d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Setor (distinto de segmento) — mesma taxonomia usada pelo motor de Score ICP
    # da Pesquisa de Leads (app/services/icp_scoring.py). Sem essa coluna, o score
    # calculado na pesquisa se perdia ao promover o lead pra empresa.
    op.add_column('companies', sa.Column('setor', sa.String(length=80), nullable=True))

    # Dossiê Comercial — resumo executivo gerado por IA
    op.add_column('companies', sa.Column('resumo_executivo', sa.Text(), nullable=True))
    op.add_column('companies', sa.Column('proxima_acao_sugerida', sa.Text(), nullable=True))
    op.add_column('companies', sa.Column('resumo_executivo_atualizado_em', sa.DateTime(timezone=True), nullable=True))

    # Dossiê Comercial — stack operacional, preenchido manualmente pelo vendedor
    op.add_column('companies', sa.Column('transportadoras', sa.Text(), nullable=True))
    op.add_column('companies', sa.Column('erp', sa.String(length=120), nullable=True))
    op.add_column('companies', sa.Column('tms', sa.String(length=120), nullable=True))

    # Dossiê Comercial — descoberta, texto livre
    op.add_column('companies', sa.Column('problemas_encontrados', sa.Text(), nullable=True))
    op.add_column('companies', sa.Column('hipoteses', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('companies', 'hipoteses')
    op.drop_column('companies', 'problemas_encontrados')
    op.drop_column('companies', 'tms')
    op.drop_column('companies', 'erp')
    op.drop_column('companies', 'transportadoras')
    op.drop_column('companies', 'resumo_executivo_atualizado_em')
    op.drop_column('companies', 'proxima_acao_sugerida')
    op.drop_column('companies', 'resumo_executivo')
    op.drop_column('companies', 'setor')
