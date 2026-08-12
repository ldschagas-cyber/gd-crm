"""DTOs de SLA Comercial (ver docs/PLANO_SLA_COMERCIAL.md)."""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.activity_sla_rule import SlaGatilhoTipo
from app.models.company import CompanyStatus
from app.models.task import TaskType
from app.schemas.common import ORMModel


class ActivitySlaRuleCreate(BaseModel):
    nome: str = Field(min_length=1, max_length=120)
    gatilho_tipo: SlaGatilhoTipo
    gatilho_valor: CompanyStatus
    prazo_horas: int = Field(gt=0)
    tipo_atividade_esperado: TaskType | None = None
    ativo: bool = True
    ordem: int = 0


class ActivitySlaRuleUpdate(BaseModel):
    nome: str | None = None
    gatilho_tipo: SlaGatilhoTipo | None = None
    gatilho_valor: CompanyStatus | None = None
    prazo_horas: int | None = Field(default=None, gt=0)
    tipo_atividade_esperado: TaskType | None = None
    ativo: bool | None = None
    ordem: int | None = None


class ActivitySlaRuleRead(ORMModel):
    id: UUID
    nome: str
    gatilho_tipo: str
    gatilho_valor: str
    prazo_horas: int
    tipo_atividade_esperado: str | None
    ativo: bool
    ordem: int
    created_at: datetime


# ---- Painel de cumprimento (motor de cálculo) --------------------------------

class SlaResumoItem(BaseModel):
    """Uma régua de SLA em curso (ou já resolvida) pra uma empresa — as três origens
    (company_status/milestone/deal_stage) chegam nesta mesma forma, unificadas em
    `ActivitySlaService.resumo()`."""
    origem: str  # 'company_status' | 'milestone' | 'deal_stage'
    regra_id: UUID
    regra_nome: str
    company_id: UUID
    empresa_nome: str
    responsavel_id: UUID | None
    gatilho_em: datetime
    prazo_em: datetime
    prazo_horas: int
    cumprida_em: datetime | None
    estado: str  # 'cumprido' | 'em_andamento' | 'em_risco' | 'estourado'
    horas_restantes: float | None
    horas_atraso: float | None
    # Só preenchido pra origem='deal_stage' — dá contexto de qual negócio gerou o item.
    deal_id: UUID | None = None
    deal_nome: str | None = None


class SlaResumoStats(BaseModel):
    em_dia: int
    em_risco: int
    estourado: int
    cumprido: int
    regras_ativas: int
    regras_total: int


class SlaResumoResponse(BaseModel):
    stats: SlaResumoStats
    items: list[SlaResumoItem]
