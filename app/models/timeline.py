"""TimelineEvent — histórico unificado de interações por empresa."""
import enum
import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin, uuid_pk


class TimelineType(str, enum.Enum):
    LIGACAO = "ligacao"
    EMAIL = "email"
    REUNIAO = "reuniao"
    TAREFA = "tarefa"
    CADASTRO = "cadastro"
    PIPELINE = "pipeline"
    NOTA = "nota"
    # Customer Success — check-in de saúde do cliente (ver app/services/health_scoring.py).
    CS_CHECKIN = "cs_checkin"


class TimelineEvent(Base, TenantMixin, TimestampMixin):
    __tablename__ = "timeline_events"

    id: Mapped[uuid.UUID] = uuid_pk()
    company_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True
    )
    deal_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("deals.id"))
    contact_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("contacts.id"))
    tipo: Mapped[str] = mapped_column(String(30), nullable=False)
    titulo: Mapped[str] = mapped_column(String(255), nullable=False)
    descricao: Mapped[str | None] = mapped_column(Text)
    evento_meta: Mapped[dict | None] = mapped_column("metadata", JSONB)
    user_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
