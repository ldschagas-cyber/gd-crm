"""Contrato e ContratoItem — vínculo produto -> proposta -> contrato -> cobrança (RF-CONTR).

Criado pré-preenchido no aceite da proposta (RF-PROP-07/RF-CONTR-06), herdando itens e
preços. Registra o `vendedor_id` (responsável comercial, RF-CONTR-07). Na ATIVAÇÃO, o
contrato reconcilia a Assinatura do cliente via evento (ponte PA-01, ver
AssinaturaService) — `assinatura_id` guarda o vínculo. O Faturamento recorrente gera
cobranças dos contratos ATIVOS (RN-F01), idempotente por contrato+competência (RN-F02).
"""
import enum
import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantMixin, TimestampMixin, uuid_pk


class ContratoStatus(str, enum.Enum):
    RASCUNHO = "rascunho"      # criado no aceite, ainda não ativado (não fatura)
    ATIVO = "ativo"            # fatura e conta como MRR
    ENCERRADO = "encerrado"


class Contrato(Base, TenantMixin, TimestampMixin):
    __tablename__ = "contratos"

    id: Mapped[uuid.UUID] = uuid_pk()
    numero: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    proposta_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("propostas.id"))
    company_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True
    )
    vendedor_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ContratoStatus.RASCUNHO.value, index=True
    )
    data_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    vigencia_meses: Mapped[int | None] = mapped_column(Integer)  # None = indeterminado
    valor_mensal: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    reajuste_indice: Mapped[str | None] = mapped_column(String(20))  # IPCA/IGP-M/Fixo
    reajuste_mes: Mapped[int | None] = mapped_column(Integer)        # mês-aniversário 1..12
    # Ponte PA-01: assinatura reconciliada por este contrato (ver AssinaturaService).
    assinatura_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("assinaturas.id"))

    itens: Mapped[list["ContratoItem"]] = relationship(
        back_populates="contrato", cascade="all, delete-orphan", lazy="selectin"
    )


class ContratoItem(Base, TenantMixin, TimestampMixin):
    __tablename__ = "contrato_itens"

    id: Mapped[uuid.UUID] = uuid_pk()
    contrato_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("contratos.id"), nullable=False, index=True
    )
    produto_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("produtos.id"), nullable=False
    )
    descricao: Mapped[str] = mapped_column(String(200), nullable=False)
    preco: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)  # herdado da proposta
    quantidade: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    contrato: Mapped["Contrato"] = relationship(back_populates="itens")
