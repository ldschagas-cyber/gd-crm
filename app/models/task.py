"""Task — atividades comerciais."""
import enum
import uuid
from datetime import date, datetime, time

from sqlalchemy import Date, DateTime, ForeignKey, String, Time
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin, uuid_pk


class TaskType(str, enum.Enum):
    LIGACAO = "ligacao"
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    REUNIAO = "reuniao"
    LINKEDIN_CONEXAO = "linkedin_conexao"
    LINKEDIN_MENSAGEM = "linkedin_mensagem"
    FOLLOWUP = "followup"


class TaskPriority(str, enum.Enum):
    BAIXA = "baixa"
    MEDIA = "media"
    ALTA = "alta"


class TaskStatus(str, enum.Enum):
    PENDENTE = "pendente"
    CONCLUIDA = "concluida"
    CANCELADA = "cancelada"


class Task(Base, TenantMixin, TimestampMixin):
    __tablename__ = "tasks"

    id: Mapped[uuid.UUID] = uuid_pk()
    titulo: Mapped[str] = mapped_column(String(255), nullable=False)
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)
    responsavel_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    company_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("companies.id"))
    contact_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("contacts.id"))
    deal_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("deals.id"))
    data: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    hora: Mapped[time | None] = mapped_column(Time)
    prioridade: Mapped[str] = mapped_column(String(20), nullable=False, default=TaskPriority.MEDIA.value)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=TaskStatus.PENDENTE.value, index=True)
    concluida_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
