"""pesquisa de leads: faixa_faturamento, origem, metas de pesquisa por usuário

Revision ID: b8f2d4a6c9e1
Revises: a3f6c1d9e2b7
Create Date: 2026-08-06 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b8f2d4a6c9e1'
down_revision: Union[str, None] = 'a3f6c1d9e2b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # faturamento (numérico livre) -> faixa_faturamento (faixas fixas, estilo LinkedIn).
    # Valores antigos viram texto do número puro (ex.: "20000000.00") — não é uma faixa
    # válida, mas não quebra nada; passam a ser tratados como "sem faixa selecionada"
    # até o usuário revisar. Não há como mapear um número solto pra uma faixa sem
    # decisão de negócio, então não tentamos aqui.
    op.alter_column('lead_prospects', 'faturamento', type_=sa.String(length=60),
                    postgresql_using='faturamento::text')
    op.alter_column('lead_prospects', 'faturamento', new_column_name='faixa_faturamento')

    op.add_column('lead_prospects', sa.Column('origem', sa.String(length=80), nullable=True))

    op.add_column('users', sa.Column('meta_pesquisa_semanal', sa.Integer(), nullable=True))
    op.add_column('users', sa.Column('meta_pesquisa_mensal', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'meta_pesquisa_mensal')
    op.drop_column('users', 'meta_pesquisa_semanal')

    op.drop_column('lead_prospects', 'origem')

    # Downgrade é melhor-esforço: linhas com faixa textual (ex.: "R$ 5–25 milhões")
    # não convertem para número e viram NULL — mesmo tipo de perda aceita em
    # d4e6f8a1b3c5_widen_faixa_funcionarios.py.
    op.alter_column('lead_prospects', 'faixa_faturamento', new_column_name='faturamento')
    op.execute("UPDATE lead_prospects SET faturamento = NULL WHERE faturamento !~ '^[0-9.]+$'")
    op.alter_column('lead_prospects', 'faturamento', type_=sa.Numeric(15, 2),
                    postgresql_using='faturamento::numeric')
