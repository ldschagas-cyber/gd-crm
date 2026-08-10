"""LeadProspect — pesquisa de leads (pré-CRM), item 9.1 da especificação."""
import enum
import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin, uuid_pk


class LeadStatus(str, enum.Enum):
    NOVO = "novo"
    ENRIQUECER = "enriquecer"
    TRIAGEM = "triagem"
    QUALIFICADO = "qualificado"
    PROMOVIDO = "promovido"
    DESCARTADO = "descartado"


class SegmentoLead(str, enum.Enum):
    """Papel da empresa na cadeia logística — taxonomia fixa (antes era texto
    livre de subcategoria). Distinto de `setor`, que é a taxonomia do Score ICP."""
    INDUSTRIA = "Indústria"
    DISTRIBUIDOR = "Distribuidor"
    TRANSPORTADORA = "Transportadora"


# Faixas de faturamento anual — estilo LinkedIn Sales Navigator. Fixas por design
# (era numérico livre antes); não entram no Score ICP, só ajudam a qualificar
# manualmente e a montar o argumento de Inteligência Comercial.
FAIXAS_FATURAMENTO = [
    "Até R$ 5 milhões",
    "R$ 5–25 milhões",
    "R$ 25–100 milhões",
    "R$ 100–500 milhões",
    "R$ 500 milhões – R$ 1 bilhão",
    "Acima de R$ 1 bilhão",
]

# Origem da pesquisa — de onde veio o interesse nesta empresa-alvo. Lista fixa
# pra dar filtro/relatório limpo; "Outro" cobre o resto.
ORIGENS_LEAD = ["Feira", "Indicação", "Campanha", "Prospecção ativa", "LinkedIn", "Outro"]


class LeadProspect(Base, TenantMixin, TimestampMixin):
    __tablename__ = "lead_prospects"

    id: Mapped[uuid.UUID] = uuid_pk()
    empresa: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    cnpj: Mapped[str | None] = mapped_column(String(14), index=True)
    setor: Mapped[str | None] = mapped_column(String(80))
    segmento: Mapped[str | None] = mapped_column(String(120))
    cidade: Mapped[str | None] = mapped_column(String(120))
    uf: Mapped[str | None] = mapped_column(String(2))
    regiao: Mapped[str | None] = mapped_column(String(20))
    faixa_funcionarios: Mapped[str | None] = mapped_column(String(50))
    faixa_faturamento: Mapped[str | None] = mapped_column(String(60))
    origem: Mapped[str | None] = mapped_column(String(80))
    site: Mapped[str | None] = mapped_column(String(255))
    telefone: Mapped[str | None] = mapped_column(String(20))
    linkedin: Mapped[str | None] = mapped_column(String(255))
    # E-mail geral/institucional da empresa (ex.: contato@empresa.com.br) — distinto do
    # e-mail de um Contato específico. Vira Company.email na promoção, mesmo uso que já
    # existe lá (não é usado por cadência/disparo automático, só informativo).
    email: Mapped[str | None] = mapped_column(String(255))
    dor_sugerida: Mapped[str | None] = mapped_column(Text)
    contato_sugerido: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=LeadStatus.NOVO.value, index=True)
    pesquisado_por: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    promoted_company_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("companies.id")
    )

    # Inteligência Comercial (JSON de CommercialIntelligenceRecord: perfil + benchmark +
    # argumento + gravado_em) — gravada manualmente pelo usuário a partir do resultado de
    # POST .../inteligencia-comercial. Copiada como está para Company.inteligencia_comercial
    # em promote() — ver app/services/lead_prospect.py.
    inteligencia_comercial: Mapped[str | None] = mapped_column(Text)
