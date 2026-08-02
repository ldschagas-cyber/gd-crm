"""Call — registro de chamadas de voz (Twilio), ligadas ou não a um registro
do CRM. Guarda o histórico bruto (duração/direção/status) independente de
haver match com Empresa/Contato/Negócio; quando há match, o serviço também
grava um TimelineEvent (tipo=ligacao) para aparecer na timeline normal.
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin, uuid_pk


class CallDirection(str, enum.Enum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"


class Call(Base, TenantMixin, TimestampMixin):
    __tablename__ = "calls"

    id: Mapped[uuid.UUID] = uuid_pk()
    call_sid: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    direcao: Mapped[str] = mapped_column(String(10), nullable=False)
    de_numero: Mapped[str | None] = mapped_column(String(20))
    para_numero: Mapped[str | None] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="iniciada")
    duracao_segundos: Mapped[int | None] = mapped_column(Integer)
    finalizada_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), index=True)
    company_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("companies.id"), index=True)
    contact_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("contacts.id"))
    deal_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("deals.id"))
