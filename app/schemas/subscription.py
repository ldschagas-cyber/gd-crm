"""DTOs de Receita Recorrente — assinaturas, eventos de MRR e indicadores.
Ver docs/PLANO_RECEITA_RECORRENTE.md."""
import enum
from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.subscription import CicloCobranca

CICLO_RE = r"^(mensal|anual)$"


class AssinaturaCreate(BaseModel):
    company_id: UUID
    deal_id: UUID | None = None
    nome_plano: str = Field(min_length=1, max_length=120)
    valor_mensal: float = Field(gt=0)
    ciclo_cobranca: str = Field(default=CicloCobranca.MENSAL.value, pattern=CICLO_RE)
    data_inicio: date
    responsavel_id: UUID | None = None


class AssinaturaValorUpdate(BaseModel):
    """Registra expansão ou contração — o serviço decide o tipo pelo sinal do delta."""
    valor_mensal: float = Field(gt=0)
    data_evento: date | None = None  # default: hoje
    observacao: str | None = Field(default=None, max_length=255)


class AssinaturaCancelar(BaseModel):
    data_cancelamento: date | None = None  # default: hoje
    motivo_cancelamento: str | None = Field(default=None, max_length=255)


class AssinaturaReativar(BaseModel):
    data_evento: date | None = None  # default: hoje
    observacao: str | None = Field(default=None, max_length=255)


class AssinaturaRead(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    company_id: UUID
    deal_id: UUID | None
    nome_plano: str
    valor_mensal: float
    ciclo_cobranca: str
    status: str
    data_inicio: date
    data_cancelamento: date | None
    motivo_cancelamento: str | None
    responsavel_id: UUID | None
    created_at: datetime


class AssinaturaEventoRead(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    assinatura_id: UUID
    tipo: str
    valor_anterior: float | None
    valor_novo: float | None
    delta_mrr: float
    data_evento: date
    observacao: str | None
    criado_por: UUID | None
    created_at: datetime


# ---- Indicadores (RevenueService) -----------------------------------------

class RevenuePeriodo(str, enum.Enum):
    MES = "mes"           # mês corrente até hoje
    ANO = "ano"            # últimos 12 meses corridos


class RevenueResumo(BaseModel):
    periodo: RevenuePeriodo
    mrr: float
    arr: float
    assinaturas_ativas: int
    novo_mrr: float
    expansao_mrr: float
    contracao_mrr: float          # negativo ou zero
    churn_mrr: float               # negativo ou zero
    net_novo_mrr: float            # novo + expansao + contracao + churn (+ reativacao)
    churn_receita_pct: float
    churn_clientes_pct: float
    nrr_pct: float
    arpa: float
    ltv: float | None              # None quando não há churn de receita no período (indefinido)


class RevenueWaterfallMes(BaseModel):
    mes: str  # AAAA-MM
    novo_mrr: float
    expansao_mrr: float
    contracao_mrr: float
    churn_mrr: float
    net_mrr: float


class RevenueWaterfall(BaseModel):
    meses: list[RevenueWaterfallMes]
