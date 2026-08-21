"""DTOs do Dashboard financeiro / Visão Geral (RF-DSH)."""
from uuid import UUID

from pydantic import BaseModel


class PendenciaRead(BaseModel):
    tipo: str          # vencida | reajuste | vigencia
    titulo: str
    valor: float | None = None
    referencia_id: UUID | None = None


class MargemVendedorRead(BaseModel):
    vendedor_id: UUID | None
    vendedor_nome: str
    propostas: int
    desconto_medio_pct: float
    desconto_max_pct: float


class FinanceiroResumo(BaseModel):
    # MRR vem do RevenueService (fonte única — decisão de PO), não recalculado aqui.
    mrr: float
    contratos_ativos: int
    a_receber_mes: float
    vencidos: float
    vencidos_qtd: int
    margem_cedida_pct: float
    pendencias: list[PendenciaRead] = []
    margem_por_vendedor: list[MargemVendedorRead] = []
