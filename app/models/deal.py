"""Deal — negócios (oportunidades comerciais)."""
import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, func, select
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, column_property, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin, uuid_pk
from app.models.timeline import TimelineEvent


class DealStatus(str, enum.Enum):
    ABERTO = "aberto"
    GANHO = "ganho"
    PERDIDO = "perdido"


class DealTipo(str, enum.Enum):
    """Distingue negócio novo (funil de vendas comum) de negócio de expansão/upsell
    aberto para um cliente já ativo — usado pelo Customer Success pra mover a empresa
    pra fase `em_expansao` enquanto o negócio está aberto (ver
    docs/PLANO_CUSTOMER_SUCCESS.md §4 e CompanyService.advance_cs_on_expansao_*). Nome
    deliberadamente distinto de `motivo_perda` (abaixo) pra não confundir "por que este
    negócio existe" com "por que este negócio foi perdido"."""
    NOVO_NEGOCIO = "novo_negocio"
    EXPANSAO = "expansao"


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
    # Previsão Comercial (ver docs/PLANO_PREVISAO_COMERCIAL.md) — o vendedor confirma que
    # este negócio fecha no mês de data_prev_fechamento, distinto da probabilidade ponderada
    # (que vem da etapa). Default False: nada é commit até alguém marcar manualmente.
    commit: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Customer Success (ver DealTipo acima). Default novo_negocio pra todo negócio já
    # existente e pra todo fluxo comum de Vendas — só vira "expansao" quando aberto
    # explicitamente a partir do drawer de um cliente no módulo de Clientes.
    tipo: Mapped[str] = mapped_column(String(20), nullable=False, default=DealTipo.NOVO_NEGOCIO.value)


# Data/hora da última interação registrada na timeline deste negócio — usada pra
# calcular "negócio parado" (§ tag de negócio, ver Pipeline > sla_horas por etapa).
# Cai pro created_at do próprio negócio quando ainda não há nenhum evento.
Deal.ultima_interacao = column_property(
    select(func.coalesce(func.max(TimelineEvent.created_at), Deal.created_at))
    .where(TimelineEvent.deal_id == Deal.id)
    .correlate_except(TimelineEvent)
    .scalar_subquery()
)
