"""DTOs dos dashboards."""
import enum
from uuid import UUID

from pydantic import BaseModel


class Periodo(str, enum.Enum):
    HOJE = "hoje"
    MES = "mes"


class FunnelStage(BaseModel):
    stage_id: UUID
    nome: str
    ordem: int
    negocios_abertos: int
    tempo_medio_parado_horas: float | None
    sla_horas: int | None


class SlaBreach(BaseModel):
    deal_id: UUID
    nome: str
    company_nome: str
    stage_nome: str
    horas_atraso: float


class SequenceExecutionBreakdown(BaseModel):
    id: UUID
    nome: str
    tipo: str
    total: int
    ativa: int
    pausada: int
    concluida: int


class CommercialDashboard(BaseModel):
    periodo: Periodo
    total_leads: int
    empresas_qualificadas: int
    negocios_ativos: int
    negocios_criados: int
    receita_prevista: float
    receita_ganha: float
    taxa_conversao: float
    ticket_medio: float
    funil: list[FunnelStage]
    sla_estourado: list[SlaBreach]
    execucao_sequencias: list[SequenceExecutionBreakdown]


class SellerDashboard(BaseModel):
    periodo: Periodo
    tarefas_pendentes: int
    tarefas_concluidas: int
    ligacoes_realizadas: int
    emails_enviados: int
    negocios_abertos: int
    receita_prevista: float
