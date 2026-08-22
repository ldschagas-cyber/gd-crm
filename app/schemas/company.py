"""DTOs de empresa."""
from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.company import CompanyStatus, CsFase, FunilEstagio
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
    # Sobrescreve CompanyBase.responsavel_id (opcional lá): empresa não pode nascer sem
    # dono — trava decidida com o usuário. CompanyUpdate não herda de CompanyBase, então
    # segue opcional (não obriga a reafirmar responsável a cada PATCH).
    responsavel_id: UUID


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
    # SDR Argos (nível 2 do agente comercial, ver docs/PLANO_SDR_AUTONOMO.md) — gerado direto
    # na empresa, automaticamente no handoff da promoção e sob demanda via POST .../sdr-argos.
    # JSON bruto de CommercialIntelligenceRecord; o frontend faz o parse.
    inteligencia_comercial: str | None
    # JSON bruto {sequence_id, sequence_nome, contato_sugerido} — SUGESTÃO, nunca inscrição
    # automática; None se nenhuma sequência ativa foi encontrada para sugerir.
    cadencia_sugerida: str | None
    roteiro_ligacao: str | None
    sdr_argos_atualizado_em: datetime | None
    # Central de Leads — None enquanto a empresa nunca entrou no funil (ver FunilEstagio).
    funil_estagio: str | None
    funil_estagio_atualizado_em: datetime | None
    # Customer Success — None enquanto a empresa nunca teve um negócio ganho (ver CsFase).
    cs_fase: str | None
    cs_fase_atualizada_em: datetime | None
    cs_responsavel_id: UUID | None
    health_score: int | None
    health_score_atualizado_em: datetime | None


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


# ---- Customer Success -------------------------------------------------------
# Ver docs/PLANO_CUSTOMER_SUCCESS.md.

class CompanyCsFaseUpdate(BaseModel):
    """Troca manual de fase (drag-and-drop no kanban ou seletor no drawer). `churn`
    nunca chega aqui — só é atingido via cancelamento de Assinatura (ver
    CompanyService.set_cs_fase e AssinaturaService.cancelar)."""
    cs_fase: CsFase


class CompanyCsUpdate(BaseModel):
    cs_responsavel_id: UUID | None = None


class HealthBreakdownItemRead(BaseModel):
    criterio: str
    valor: str
    pontos: int


class HealthScoreRead(BaseModel):
    score: int
    faixa: str  # 'saudavel' | 'atencao' | 'em_risco'
    engajamento: int
    uso: int
    satisfacao: int
    financeiro: int
    precisa_checkin: bool
    breakdown: list[HealthBreakdownItemRead]


class CsCheckinCreate(BaseModel):
    uso_percebido: int = Field(ge=0, le=100)
    satisfacao: int = Field(ge=0, le=100)
    notas: str | None = None


class AssinaturaResumoRead(BaseModel):
    """Recorte da Assinatura ativa (ou mais recente) exibido no drawer de Clientes —
    evita o frontend ter que combinar duas chamadas pra montar a aba de Renovação."""
    id: UUID
    nome_plano: str
    valor_mensal: float
    status: str
    data_inicio: date
    ciclo_renovacao_meses: int | None
    data_renovacao: date | None


class ClienteRead(BaseModel):
    """Uma linha do módulo de Clientes — Company enriquecida com Health Score,
    checklist de implantação e assinatura, análoga a CentralLeadRead pra Central de
    Leads. Não substitui CompanyRead."""
    id: UUID
    razao_social: str
    nome_fantasia: str | None
    segmento: str | None
    uf: str | None
    cs_fase: str
    cs_fase_atualizada_em: datetime | None
    cs_responsavel_id: UUID | None
    ultima_interacao: datetime
    health_score: int | None
    health_faixa: str | None
    onboarding_progresso: int  # 0-100; 100 quando não há checklist (nada a fazer)
    assinatura: AssinaturaResumoRead | None
    expansao_aberta: bool  # existe negócio tipo=expansao aberto


class CsFaseCountRead(BaseModel):
    fase: str
    total: int


class ClientesResumo(BaseModel):
    total: int  # exclui 'churn'
    mrr_total: float
    arr_total: float
    health_medio: int
    em_risco: int
    renovacao_60d: int
    por_fase: list[CsFaseCountRead]
