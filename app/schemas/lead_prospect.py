"""Schemas de pesquisa de leads e critérios de pontuação (ICP)."""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.lead_prospect import LeadStatus


class LeadProspectCreate(BaseModel):
    empresa: str = Field(min_length=1, max_length=255)
    setor: str | None = None
    segmento: str | None = None
    uf: str | None = Field(default=None, max_length=2)
    regiao: str | None = None
    faixa_funcionarios: str | None = None
    faturamento: float | None = None
    site: str | None = None
    telefone: str | None = None
    linkedin: str | None = None
    dor_sugerida: str | None = None
    contato_sugerido: str | None = None
    status: LeadStatus = LeadStatus.NOVO
    pesquisado_por: UUID


class LeadProspectUpdate(BaseModel):
    empresa: str | None = Field(default=None, min_length=1, max_length=255)
    setor: str | None = None
    segmento: str | None = None
    uf: str | None = Field(default=None, max_length=2)
    regiao: str | None = None
    faixa_funcionarios: str | None = None
    faturamento: float | None = None
    site: str | None = None
    telefone: str | None = None
    linkedin: str | None = None
    dor_sugerida: str | None = None
    contato_sugerido: str | None = None
    status: LeadStatus | None = None
    pesquisado_por: UUID | None = None


class LeadProspectRead(BaseModel):
    id: UUID
    empresa: str
    setor: str | None
    segmento: str | None
    uf: str | None
    regiao: str | None
    faixa_funcionarios: str | None
    faturamento: float | None
    site: str | None
    telefone: str | None
    linkedin: str | None
    dor_sugerida: str | None
    contato_sugerido: str | None
    status: str
    pesquisado_por: UUID
    promoted_company_id: UUID | None
    created_at: datetime
    # calculados a partir de tenants.config.icp_scoring_rules — nunca persistidos
    score_icp: int
    icp_fit: str
    gamificacao: int
    recebe_bonus: bool
    bonus_valor: float


class LeadProspectPageParams(BaseModel):
    """Paginação com teto maior que o PageParams padrão: a lista busca tudo e
    filtra/pagina em memória (icp_fit é calculado, não é coluna) — volume
    esperado é baixo (pesquisa manual), não os milhares de outras listagens."""
    page: int = Field(1, ge=1)
    size: int = Field(200, ge=1, le=1000)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size


class LeadEnrichmentSuggestion(BaseModel):
    """Sugestões geradas por IA a partir de pesquisa na web — nunca salvas
    automaticamente, sempre revisadas pelo usuário antes de aplicar ao lead."""
    setor: str | None = None
    segmento: str | None = None
    uf: str | None = None
    faixa_funcionarios: str | None = None
    faturamento: float | None = None
    site: str | None = None
    telefone: str | None = None
    linkedin: str | None = None
    contato_sugerido: str | None = None
    dor_sugerida: str | None = None
    observacoes: str | None = None


class PerformanceReportRow(BaseModel):
    """Uma linha agregada por pesquisador dentro do mês do relatório (§9.7)."""
    pesquisador_id: UUID
    pesquisador_nome: str
    total: int
    icp_a: int
    icp_b: int
    icp_c: int
    sem_perfil: int
    taxa_qualificacao: int  # percentual 0-100 = (icp_a + icp_b) / total
    promovidos: int
    bonus_valido: float


class PerformanceReportResponse(BaseModel):
    mes: str
    rows: list[PerformanceReportRow]


class IcpScoringRules(BaseModel):
    setor: dict[str, int] = {}
    setor_fallback: int = 10
    regiao: dict[str, int] = {}
    faixa_funcionarios: dict[str, int] = {}
    corte_a: int = 80
    corte_b: int = 70
    corte_c: int = 40
    bonus_valor: float = 1.0
