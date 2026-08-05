"""DTOs de empresa."""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.company import CompanyStatus
from app.schemas.common import ORMModel


class CompanyBase(BaseModel):
    razao_social: str = Field(min_length=1, max_length=255)
    nome_fantasia: str | None = None
    cnpj: str | None = Field(default=None, max_length=14)
    site: str | None = None
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
    origem: str | None = None
    responsavel_id: UUID | None = None
    contexto_rapido: str | None = None


class CompanyCreate(CompanyBase):
    status: CompanyStatus = CompanyStatus.LEAD


class CompanyUpdate(BaseModel):
    razao_social: str | None = None
    nome_fantasia: str | None = None
    site: str | None = None
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
    origem: str | None = None
    responsavel_id: UUID | None = None
    contexto_rapido: str | None = None


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
    # JSON bruto de CommercialIntelligenceRecord — só chega aqui por cópia automática na
    # promoção do LeadProspect (ver LeadProspectService.promote()); sem endpoint próprio.
    inteligencia_comercial: str | None


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
