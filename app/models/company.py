"""Company — empresas (leads e clientes) do tenant."""
import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func, select
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, column_property, mapped_column

from app.models.base import Base, SoftDeleteMixin, TenantMixin, TimestampMixin, uuid_pk
from app.models.timeline import TimelineEvent


# Origem do cadastro — lista fixa pra dar filtro/relatório limpo (mesmo espírito de
# ORIGENS_LEAD em lead_prospect.py). O Negócio herda esse valor da empresa na criação
# (ver DealService.create) em vez de ter origem própria — ver app/services/deal.py.
ORIGENS_EMPRESA = [
    "Indicação", "Prospecção ativa", "Feira", "Campanha", "LinkedIn",
    "Site institucional", "Formulário do site", "Pesquisa de Leads", "Outro",
]


class CompanyStatus(str, enum.Enum):
    LEAD = "lead"
    QUALIFICADO = "qualificado"
    CLIENTE = "cliente"
    PERDIDO = "perdido"
    INATIVO = "inativo"


class FunilEstagio(str, enum.Enum):
    """Estágio no funil da Central de Leads — independente de `CompanyStatus` (que
    continua regendo lead/cliente/perdido). `None` = empresa nunca entrou no funil
    (não aparece na Central de Leads). MQL e SQL são sempre transição manual — nunca
    atingidos automaticamente pelo Lead Score. Ver docs/PLANO_CENTRAL_DE_LEADS.md."""
    NOVO = "novo"
    QUALIFICANDO = "qualificando"
    CADENCIA = "cadencia"
    MQL = "mql"
    SQL = "sql"
    CONVERTIDO = "convertido"


class Company(Base, TenantMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "companies"
    __table_args__ = (
        UniqueConstraint("tenant_id", "cnpj", name="uq_company_tenant_cnpj"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    razao_social: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    nome_fantasia: Mapped[str | None] = mapped_column(String(255))
    cnpj: Mapped[str | None] = mapped_column(String(14))
    site: Mapped[str | None] = mapped_column(String(255))
    telefone: Mapped[str | None] = mapped_column(String(20))
    email: Mapped[str | None] = mapped_column(String(255))
    endereco: Mapped[str | None] = mapped_column(String(255))
    cidade: Mapped[str | None] = mapped_column(String(120))
    uf: Mapped[str | None] = mapped_column(String(2))
    segmento: Mapped[str | None] = mapped_column(String(120))
    porte: Mapped[str | None] = mapped_column(String(40))
    num_funcionarios: Mapped[int | None] = mapped_column(Integer)
    faturamento_estimado: Mapped[float | None] = mapped_column(Numeric(15, 2))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=CompanyStatus.LEAD.value, index=True)
    origem: Mapped[str | None] = mapped_column(String(80))
    responsavel_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    created_by: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))

    # Central de Leads — funil pós-promoção (ver FunilEstagio acima). NULL = fora do funil.
    funil_estagio: Mapped[str | None] = mapped_column(String(20), index=True)
    funil_estagio_atualizado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Nota curta de personalização, usada em {{contexto_rapido}} nos e-mails automáticos
    # (ver app/services/sequence_dispatch.py:render_template) — equivalente, em nível de
    # empresa, ao contexto_pessoal do Contato.
    contexto_rapido: Mapped[str | None] = mapped_column(Text)

    # Setor — taxonomia do motor de Score ICP (app/services/icp_scoring.py), distinta
    # de `segmento` (texto livre). Preenchida na promoção de um LeadProspect ou
    # manualmente, pra empresa poder ter score/fit calculado no Dossiê Comercial.
    setor: Mapped[str | None] = mapped_column(String(80))

    # Dossiê Comercial — resumo executivo gerado por IA, regenerado automaticamente
    # a cada evento relevante na timeline (ver app/services/company_ai.py).
    resumo_executivo: Mapped[str | None] = mapped_column(Text)
    proxima_acao_sugerida: Mapped[str | None] = mapped_column(Text)
    resumo_executivo_atualizado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Dossiê Comercial — stack operacional, preenchimento manual do vendedor na descoberta.
    transportadoras: Mapped[str | None] = mapped_column(Text)
    erp: Mapped[str | None] = mapped_column(String(120))
    tms: Mapped[str | None] = mapped_column(String(120))

    # Dossiê Comercial — descoberta, texto livre.
    problemas_encontrados: Mapped[str | None] = mapped_column(Text)
    hipoteses: Mapped[str | None] = mapped_column(Text)

    # Dossiê Comercial — Inteligência Comercial (mesmo JSON de LeadProspect.inteligencia_comercial).
    # Só chega aqui por cópia automática em LeadProspectService.promote(); não há endpoint de
    # geração/gravação própria da Company — a geração acontece sempre no lead, antes de promover.
    inteligencia_comercial: Mapped[str | None] = mapped_column(Text)


# Data/hora da última interação registrada na timeline desta empresa — mesmo padrão de
# Deal.ultima_interacao (app/models/deal.py), usado pela Central de Leads pra "última
# interação" e pra marcar lead parado. Cai pro created_at da própria empresa sem eventos.
Company.ultima_interacao = column_property(
    select(func.coalesce(func.max(TimelineEvent.created_at), Company.created_at))
    .where(TimelineEvent.company_id == Company.id)
    .correlate_except(TimelineEvent)
    .scalar_subquery()
)
