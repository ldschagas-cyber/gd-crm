"""Deal — negócios (oportunidades comerciais)."""
import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, func, select
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, column_property, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin, uuid_pk
from app.models.timeline import TimelineEvent


class DealStatus(str, enum.Enum):
    ABERTO = "aberto"
    GANHO = "ganho"
    PERDIDO = "perdido"


class Deal(Base, TenantMixin, TimestampMixin):
    __tablename__ = "deals"

    id: Mapped[uuid.UUID] = uuid_pk()
    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    company_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True
    )
    contact_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("contacts.id"))
    responsavel_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    pipeline_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("pipelines.id"), nullable=False)
    stage_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("pipeline_stages.id"), nullable=False, index=True
    )
    valor_previsto: Mapped[float | None] = mapped_column(Numeric(15, 2))
    probabilidade: Mapped[int | None] = mapped_column(Integer)
    data_prev_fechamento: Mapped[date | None] = mapped_column(Date)
    origem: Mapped[str | None] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=DealStatus.ABERTO.value, index=True)
    motivo_perda: Mapped[str | None] = mapped_column(String(255))
    data_fechamento: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


# Data/hora da última interação registrada na timeline deste negócio — usada pra
# calcular "negócio parado" (§ tag de negócio, ver Pipeline > sla_horas por etapa).
# Cai pro created_at do próprio negócio quando ainda não há nenhum evento.
Deal.ultima_interacao = column_property(
    select(func.coalesce(func.max(TimelineEvent.created_at), Deal.created_at))
    .where(TimelineEvent.deal_id == Deal.id)
    .correlate_except(TimelineEvent)
    .scalar_subquery()
)
