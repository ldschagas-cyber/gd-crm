"""DTOs de empresa."""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.company import CompanyStatus, FunilEstagio
from app.schemas.common import ORMModel


class CompanyBase(BaseModel):
    razao_social: str = Field(min_length=1, max_length=255)
    nome_fantasia: str | None = None
    cnpj: str | None = Field(default=None, max_length=14)
    site: str | None = None
    linkedin: str | None = None
    telefone: str | None = None
    email: str | None = None
    endereco: str | None = None
    cidade: str | None = None
    uf: str | None = Field(default=None, max_length=2)
    segmento: str | None = None
    setor: str | None = None
    porte: str | None = None
    num_funcionarios: int | None = None
    faturamento_estimado: float | None = None
    faixa_faturamento: str | None = None
    origem: str | None = None
    responsavel_id: UUID | None = None
    contexto_rapido: str | None = None
    contato_sugerido: str | None = None


class CompanyCreate(CompanyBase):
    status: CompanyStatus = CompanyStatus.LEAD


class CompanyUpdate(BaseModel):
    razao_social: str | None = None
    nome_fantasia: str | None = None
    site: str | None = None
    linkedin: str | None = None
    telefone: str | None = None
    email: str | None = None
    endereco: str | None = None
    cidade: str | None = None
    uf: str | None = None
    segmento: str | None = None
    setor: str | None = None
    porte: str | None = None
    num_funcionarios: int | None = None
    faturamento_estimado: float | None = None
    faixa_faturamento: str | None = None
    origem: str | None = None
    responsavel_id: UUID | None = None
    contexto_rapido: str | None = None
    contato_sugerido: str | None = None


class CompanyDossierUpdate(BaseModel):
    """Campos do Dossiê Comercial preenchidos manualmente pelo vendedor."""
    transportadoras: str | None = None
    erp: str | None = None
    tms: str | None = None
    problemas_encontrados: str | None = None
    hipoteses: str | None = None


class CompanyStatusUpdate(BaseModel):
    status: CompanyStatus


class CompanyFilterOptions(BaseModel):
    """Valores distintos já cadastrados, para popular os filtros da grade
    (segmento/porte/origem/uf não têm lista fixa — são texto livre no cadastro)."""
    segmento: list[str] = []
    porte: list[str] = []
    origem: list[str] = []
    uf: list[str] = []


class CompanyRead(ORMModel):
    id: UUID
    razao_social: str
    nome_fantasia: str | None
    cnpj: str | None
    site: str | None
    linkedin: str | None
    telefone: str | None
    email: str | None
    endereco: str | None
    cidade: str | None
    uf: str | None
    segmento: str | None
    setor: str | None
    porte: str | None
    num_funcionarios: int | None
    faturamento_estimado: float | None
    faixa_faturamento: str | None
    status: str
    origem: str | None
    responsavel_id: UUID | None
    contexto_rapido: str | None
    created_at: datetime
    resumo_executivo: str | None
    proxima_acao_sugerida: str | None
    resumo_executivo_atualizado_em: datetime | None
    transportadoras: str | None
    erp: str | None
    tms: str | None
    problemas_encontrados: str | None
    hipoteses: str | None
    contato_sugerido: str | None
    # JSON bruto de CommercialIntelligenceRecord — só chega aqui por cópia automática na
    # promoção do LeadProspect (ver LeadProspectService.promote()); sem endpoint próprio.
    inteligencia_comercial: str | None
    # Central de Leads — None enquanto a empresa nunca entrou no funil (ver FunilEstagio).
    funil_estagio: str | None
    funil_estagio_atualizado_em: datetime | None


class IcpBreakdownItemRead(BaseModel):
    criterio: str
    valor: str
    pontos: int


class CompanyIcpRead(BaseModel):
    score: int
    fit: str
    breakdown: list[IcpBreakdownItemRead]


class CompanyAskRequest(BaseModel):
    pergunta: str = Field(min_length=1, max_length=500)


class CompanyAskResponse(BaseModel):
    resposta: str
    fontes: list[str]


# ---- Central de Leads --------------------------------------------------------

class CompanyFunilEstagioUpdate(BaseModel):
    """Troca manual de estágio (drag-and-drop no kanban ou seletor no drawer). MQL e
    SQL só chegam aqui por este endpoint — nunca por um gatilho automático do backend
    (promoção, inscrição em cadência, criação de negócio). Ver plano §3."""
    funil_estagio: FunilEstagio


class LeadScoreRules(BaseModel):
    """Pesos do componente de Engajamento do Lead Score — o componente de Fit ICP
    continua sendo `IcpScoringRules` (Pesquisa de Leads). Lead Score = 60% ICP + 40%
    engajamento, pesos de mistura fixos por ora (não expostos aqui)."""
    eventos: dict[str, int] = {}
    etapa_cadencia_concluida: int = 5
    decaimento_por_semana_sem_interacao: int = 10
    quente_a_partir_de: int = 70
    morno_a_partir_de: int = 40


class ProximaAcaoRead(BaseModel):
    tipo: str  # 'tarefa' (task aberta mais próxima) ou 'ia' (proxima_acao_sugerida do Dossiê)
    texto: str
    data: datetime | None = None


class CadenciaInfoRead(BaseModel):
    enrollment_id: UUID
    sequence_id: UUID
    nome: str
    etapa_atual: int
    total_etapas: int


class CentralLeadRead(BaseModel):
    """Uma linha da Central de Leads — Company enriquecida com Lead Score, cadência
    ativa e próxima ação. Não substitui CompanyRead (usado em Empresas); é uma visão
    combinada específica pro funil, análoga ao que LeadProspectRead é pra Pesquisa
    de Leads."""
    id: UUID
    razao_social: str
    nome_fantasia: str | None
    segmento: str | None
    uf: str | None
    origem: str | None
    responsavel_id: UUID | None
    funil_estagio: str
    funil_estagio_atualizado_em: datetime | None
    ultima_interacao: datetime
    score_icp: int
    score_engajamento: int
    lead_score: int
    temperatura: str
    proxima_acao: ProximaAcaoRead | None
    cadencia: CadenciaInfoRead | None
    convertido_em: datetime | None = None


class EstagioCountRead(BaseModel):
    estagio: str
    total: int


class CentralLeadsResumo(BaseModel):
    total: int
    total_ativos: int  # exclui 'convertido' — ver decisão de produto (convertidos ficam visíveis, mas fora da contagem de "ativos")
    por_estagio: list[EstagioCountRead]
    score_medio: int
    parados: int  # sem interação há 7+ dias, exclui 'convertido'
