"""LeadProspect — pesquisa de leads (pré-CRM), item 9.1 da especificação."""
import enum
import uuid

from sqlalchemy import ForeignKey, Numeric, String, Text
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


class LeadProspect(Base, TenantMixin, TimestampMixin):
    __tablename__ = "lead_prospects"

    id: Mapped[uuid.UUID] = uuid_pk()
    empresa: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    setor: Mapped[str | None] = mapped_column(String(80))
    segmento: Mapped[str | None] = mapped_column(String(120))
    uf: Mapped[str | None] = mapped_column(String(2))
    regiao: Mapped[str | None] = mapped_column(String(20))
    faixa_funcionarios: Mapped[str | None] = mapped_column(String(20))
    faturamento: Mapped[float | None] = mapped_column(Numeric(15, 2))
    site: Mapped[str | None] = mapped_column(String(255))
    telefone: Mapped[str | None] = mapped_column(String(20))
    linkedin: Mapped[str | None] = mapped_column(String(255))
    dor_sugerida: Mapped[str | None] = mapped_column(Text)
    contato_sugerido: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=LeadStatus.NOVO.value, index=True)
    pesquisado_por: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    promoted_company_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("companies.id")
    )
