"""add modulo financeiro (produtos, propostas, contratos, cobrancas, categorias)

Cria as tabelas da Fase 1 do módulo Financeiro e habilita RLS por tenant em todas
(chancela #2: toda tabela nova nasce com política RLS, lendo app.current_tenant —
mesmo padrão do 0001_initial). As tabelas são criadas a partir do metadata dos modelos
(fonte única de verdade), o que resolve automaticamente a FK circular propostas<->contratos.

Revision ID: c4f7a2b9e1d3
Revises: d9e1f3a5c7b2
Create Date: 2026-08-21 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op

from app.models import Base
from app.models.billing import Cobranca
from app.models.contract import Contrato, ContratoItem
from app.models.finance_category import CategoriaFinanceira
from app.models.product import Produto, ProdutoPrecoHist
from app.models.proposal import Proposta, PropostaItem

revision: str = "c4f7a2b9e1d3"
down_revision: Union[str, None] = "d9e1f3a5c7b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Ordem de criação irrelevante (create_all resolve dependências); a de drop é a inversa.
_MODELS = [
    Produto, ProdutoPrecoHist, CategoriaFinanceira,
    Proposta, PropostaItem, Contrato, ContratoItem, Cobranca,
]
TENANT_TABLES = [m.__tablename__ for m in _MODELS]


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind, tables=[m.__table__ for m in _MODELS])

    # Índices compostos tenant-first para as consultas mais frequentes do módulo.
    op.create_index("ix_cobrancas_tenant_status_venc", "cobrancas",
                    ["tenant_id", "status", "vencimento"])
    op.create_index("ix_propostas_tenant_status", "propostas", ["tenant_id", "status"])
    op.create_index("ix_contratos_tenant_status", "contratos", ["tenant_id", "status"])

    # Row-Level Security: mesma política do 0001_initial (defesa em profundidade).
    for table in TENANT_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY tenant_isolation ON {table} "
            f"USING (tenant_id = current_setting('app.current_tenant', true)::uuid)"
        )


def downgrade() -> None:
    bind = op.get_bind()
    for table in TENANT_TABLES:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
    op.drop_index("ix_contratos_tenant_status", table_name="contratos")
    op.drop_index("ix_propostas_tenant_status", table_name="propostas")
    op.drop_index("ix_cobrancas_tenant_status_venc", table_name="cobrancas")
    Base.metadata.drop_all(bind=bind, tables=[m.__table__ for m in reversed(_MODELS)])
