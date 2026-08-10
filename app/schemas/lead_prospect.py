"""Schemas de pesquisa de leads e critérios de pontuação (ICP)."""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.lead_prospect import LeadStatus, SegmentoLead


class LeadProspectCreate(BaseModel):
    empresa: str = Field(min_length=1, max_length=255)
    cnpj: str | None = Field(default=None, max_length=14)
    setor: str | None = None
    segmento: SegmentoLead | None = None
    uf: str | None = Field(default=None, max_length=2)
    regiao: str | None = None
    faixa_funcionarios: str | None = None
    faixa_faturamento: str | None = None
    origem: str | None = None
    site: str | None = None
    telefone: str | None = None
    linkedin: str | None = None
    dor_sugerida: str | None = None
    contato_sugerido: str | None = None
    status: LeadStatus = LeadStatus.NOVO
    pesquisado_por: UUID


class LeadProspectUpdate(BaseModel):
    empresa: str | None = Field(default=None, min_length=1, max_length=255)
    cnpj: str | None = Field(default=None, max_length=14)
    setor: str | None = None
    segmento: SegmentoLead | None = None
    uf: str | None = Field(default=None, max_length=2)
    regiao: str | None = None
    faixa_funcionarios: str | None = None
    faixa_faturamento: str | None = None
    origem: str | None = None
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
    cnpj: str | None
    setor: str | None
    segmento: str | None
    uf: str | None
    regiao: str | None
    faixa_funcionarios: str | None
    faixa_faturamento: str | None
    origem: str | None
    site: str | None
    telefone: str | None
    linkedin: str | None
    dor_sugerida: str | None
    contato_sugerido: str | None
    status: str
    pesquisado_por: UUID
    promoted_company_id: UUID | None
    created_at: datetime
    # JSON bruto de CommercialIntelligenceRecord (perfil + benchmark + argumento + gravado_em),
    # ou None se a Inteligência Comercial nunca foi gravada para este lead. O frontend faz o parse.
    inteligencia_comercial: str | None
    # calculados a partir de tenants.config.icp_scoring_rules — nunca persistidos
    score_icp: int
    icp_fit: str
    gamificacao: int
    recebe_bonus: bool
    bonus_valor: float


class LeadPromoteRequest(BaseModel):
    """Corpo opcional de POST /{lead_id}/promote — permite já indicar o
    responsável da Company recém-criada no ato da promoção (individual ou em
    lote), sem precisar de um segundo passo em Central de Leads/Empresas."""
    responsavel_id: UUID | None = None


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
    faixa_faturamento: str | None = None
    site: str | None = None
    telefone: str | None = None
    linkedin: str | None = None
    contato_sugerido: str | None = None
    dor_sugerida: str | None = None
    observacoes: str | None = None


class CommercialIntelligencePerfil(BaseModel):
    """Perfil pesquisado na web — mesma natureza do LeadEnrichmentSuggestion:
    pode conter imprecisões, é sempre exibido com a fonte à vista (pesquisa)."""
    erp: str | None = None
    porte_estimado: str | None = None
    atuacao: str | None = None
    operacao_transporte: str | None = None


class CommercialIntelligenceBenchmark(BaseModel):
    """Referência de mercado do Benchmark Setorial (Diagnóstico) — NUNCA uma
    medição desta empresa específica, que ainda não é cliente e não tem CT-e
    no sistema. `disponivel=False` cobre tanto "setor sem mapeamento" quanto
    "Diagnóstico não respondeu" — o relatório segue sem travar nesses casos."""
    disponivel: bool
    segmento_pesquisado: str | None = None
    segmento_diagnostico: str | None = None
    frete_kg_medio: float | None = None
    motivo_indisponivel: str | None = None


class CommercialIntelligenceResponse(BaseModel):
    """Sugestão gerada por IA — nunca salva automaticamente. Item 'Inteligência
    Comercial' da Pesquisa de Leads: cruza o perfil pesquisado da empresa com o
    Benchmark Logístico do GD Diagnóstico para montar um argumento comercial."""
    perfil: CommercialIntelligencePerfil
    benchmark: CommercialIntelligenceBenchmark
    argumento: str


class CommercialIntelligenceRecord(CommercialIntelligenceResponse):
    """O mesmo resultado acima, mas gravado: é o formato serializado (via
    model_dump_json) em LeadProspect.inteligencia_comercial e, por cópia na
    promoção, em Company.inteligencia_comercial. `gravado_em` é definido pelo
    servidor no momento do PATCH — nunca vem do cliente."""
    gravado_em: datetime


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


class MetaProgressRow(BaseModel):
    """Progresso de um pesquisador contra a meta de pesquisa (semana/mês corrente,
    independente do mês selecionado no relatório de desempenho). `meta_*=None`
    significa que o admin não definiu meta pra esse usuário ainda."""
    pesquisador_id: UUID
    pesquisador_nome: str
    pesquisas_semana: int
    meta_semanal: int | None
    pesquisas_mes: int
    meta_mensal: int | None


class MetaProgressResponse(BaseModel):
    rows: list[MetaProgressRow]


class IcpScoringRules(BaseModel):
    setor: dict[str, int] = {}
    setor_fallback: int = 10
    regiao: dict[str, int] = {}
    faixa_funcionarios: dict[str, int] = {}
    corte_a: int = 80
    corte_b: int = 70
    corte_c: int = 40
    bonus_valor: float = 1.0
