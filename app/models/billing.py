"""Cobranca — o recebível gerado pelo faturamento (RF-CAR).

Contas a Receber = faturamento: a cobrança é o próprio recebível. Geração idempotente
por contrato+competência (RN-F02) — garantida pela UniqueConstraint abaixo. A baixa
(status `paga`, valor_recebido, data_baixa) é da tela Contas a Receber (lote seguinte);
aqui as cobranças nascem `aberta`. `nf_solicitada_em` registra o pedido de NF ao contador
disparado no faturamento (o contador emite a NFS-e; o sistema não emite — ver
ContadorService). NADA é excluído fisicamente (status `cancelada`, RN-F06).
"""
import enum
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin, uuid_pk


class CobrancaStatus(str, enum.Enum):
    ABERTA = "aberta"
    PAGA = "paga"
    VENCIDA = "vencida"
    CANCELADA = "cancelada"


class CobrancaTipo(str, enum.Enum):
    RECORRENTE = "recorrente"
    PONTUAL = "pontual"


class Cobranca(Base, TenantMixin, TimestampMixin):
    __tablename__ = "cobrancas"
    __table_args__ = (
        # Idempotência do faturamento recorrente (RN-F02): um contrato só gera uma
        # cobrança por competência. Cobrança pontual tem contrato_id NULL (NULLs são
        # distintos no Postgres) — não colide entre si nem trava avulsas.
        UniqueConstraint("tenant_id", "contrato_id", "competencia", name="uq_cobranca_contrato_competencia"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    contrato_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("contratos.id"), index=True
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True
    )
    categoria_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("categorias_financeiras.id")
    )
    competencia: Mapped[str] = mapped_column(String(7), nullable=False, index=True)  # AAAA-MM
    descricao: Mapped[str] = mapped_column(String(200), nullable=False)
    tipo: Mapped[str] = mapped_column(String(12), nullable=False, default=CobrancaTipo.RECORRENTE.value)
    valor: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    vencimento: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(12), nullable=False, default=CobrancaStatus.ABERTA.value, index=True)
    valor_recebido: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    data_baixa: Mapped[date | None] = mapped_column(Date)
    # Pedido de NF ao contador (gatilho no faturamento). NULL = ainda não solicitado.
    nf_solicitada_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    nf_numero: Mapped[str | None] = mapped_column(String(40))
