"""DTOs de investimento comercial e CAC/ROI. Ver docs/PLANO_PREVISAO_COMERCIAL.md §8."""
from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel

CATEGORIA_RE = r"^(marketing|vendas|ferramentas|outros)$"


class RevenueInvestmentCreate(BaseModel):
    mes: str = Field(description="Mês de competência no formato AAAA-MM")
    categoria: str = Field(pattern=CATEGORIA_RE)
    valor: float = Field(gt=0)
    observacao: str | None = Field(default=None, max_length=255)


class RevenueInvestmentUpdate(BaseModel):
    categoria: str | None = Field(default=None, pattern=CATEGORIA_RE)
    valor: float | None = Field(default=None, gt=0)
    observacao: str | None = Field(default=None, max_length=255)


class RevenueInvestmentRead(ORMModel):
    id: UUID
    competencia: date
    categoria: str
    valor: float
    observacao: str | None
    criado_por: UUID | None


class CacRoiResumo(BaseModel):
    mes: str  # AAAA-MM
    investimento_total: float
    clientes_novos: int  # FunilMetasResumo, etapa "fechados" (modo atividade)
    receita_realizada: float  # FunilMetasResumo.fechados_valor_realizado
    cac: float | None  # None (não 0) quando não há clientes fechados — indefinido, não grátis
    roi: float | None  # None (não 0) quando não há investimento lançado — indefinido, não 0%
