"""add deal_itens (linha de produto no negócio)

Cobre o fluxo de venda que fecha direto no Kanban sem passar por uma Proposta
formal: o negócio ganha linhas de produto (mesmo padrão de PropostaItem/
ContratoItem), e a Receita Recorrente passa a somar os itens RECORRENTE em vez
de tratar `valor_previsto` como contrato anual e dividir por 12 (ver
AssinaturaService.registrar_negocio_ganho / ContratoService._mrr_estimado_do_negocio).
Mesmo padrão de RLS da c4f7a2b9e1d3 (add modulo financeiro).

Revision ID: a3d8f1c6b904
Revises: 56d39be2c889
Create Date: 2026-08-22 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op

from app.models import Base
from app.models.deal import DealItem

revision: str = "a3d8f1c6b904"
down_revision: Union[str, None] = "56d39be2c889"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind, tables=[DealItem.__table__])
    op.execute("ALTER TABLE deal_itens ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE deal_itens FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON deal_itens "
        "USING (tenant_id = current_setting('app.current_tenant', true)::uuid)"
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON deal_itens")
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind, tables=[DealItem.__table__])
