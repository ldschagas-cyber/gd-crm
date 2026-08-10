"""DTOs de Previsão Comercial (Forecast/Commit). Ver docs/PLANO_PREVISAO_COMERCIAL.md."""
from datetime import date
from uuid import UUID

from pydantic import BaseModel


class ForecastNegocio(BaseModel):
    id: UUID
    nome: str
    company_nome: str
    responsavel_id: UUID
    responsavel_nome: str
    stage_nome: str
    valor_previsto: float
    probabilidade: int | None
    data_prev_fechamento: date | None
    commit: bool


class ForecastVendedor(BaseModel):
    responsavel_id: UUID
    nome: str
    negocios: int
    pipeline: float
    forecast: float
    commit: float


class ForecastResumo(BaseModel):
    mes: str  # AAAA-MM
    pipeline_total: float
    forecast_total: float
    commit_total: float
    por_vendedor: list[ForecastVendedor]
    negocios: list[ForecastNegocio]
