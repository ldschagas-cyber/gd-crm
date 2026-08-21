"""Proposta e PropostaItem — orçamento com CAPTURA de desconto (RF-PROP).

Escopo Fase 1 revisada: o desconto é sempre CALCULADO (1 - preco_proposto/preco_tabela,
RN-F09) e registrado por item com snapshot do preço de tabela (RN-F13) — é o dado que
alimenta a margem cedida no dashboard. A GOVERNANÇA de desconto (alçadas, fila de
aprovação, painel acumulado v1->vN, bloqueio de piso) fica para a fase seguinte: aqui só
se captura e exibe. Aceite de proposta gera contrato pré-preenchido (RF-PROP-07).
"""
import enum
import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantMixin, TimestampMixin, uuid_pk


class PropostaStatus(str, enum.Enum):
    RASCUNHO = "rascunho"
    ENVIADA = "enviada"
    EM_NEGOCIACAO = "em_negociacao"
    ACEITA = "aceita"
    RECUSADA = "recusada"
    EXPIRADA = "expirada"


class Proposta(Base, TenantMixin, TimestampMixin):
    __tablename__ = "propostas"

    id: Mapped[uuid.UUID] = uuid_pk()
    numero: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    deal_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("deals.id"))
    company_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True
    )
    vendedor_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    versao: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=PropostaStatus.RASCUNHO.value, index=True
    )
    validade: Mapped[date | None] = mapped_column(Date)
    observacao: Mapped[str | None] = mapped_column(Text)
    # Totais derivados dos itens, persistidos para listagem/dashboard sem recomputar.
    valor_tabela_total: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    valor_proposto_total: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    desconto_pct_total: Mapped[Decimal] = mapped_column(Numeric(6, 3), nullable=False, default=0)
    contrato_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("contratos.id"))
    created_by: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))

    itens: Mapped[list["PropostaItem"]] = relationship(
        back_populates="proposta", cascade="all, delete-orphan", lazy="selectin"
    )


class PropostaItem(Base, TenantMixin, TimestampMixin):
    __tablename__ = "proposta_itens"

    id: Mapped[uuid.UUID] = uuid_pk()
    proposta_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("propostas.id"), nullable=False, index=True
    )
    produto_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("produtos.id"), nullable=False
    )
    descricao: Mapped[str] = mapped_column(String(200), nullable=False)
    preco_tabela: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)  # snapshot (RN-F13)
    preco_proposto: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    desconto_pct: Mapped[Decimal] = mapped_column(Numeric(6, 3), nullable=False, default=0)  # calculado (RN-F09)
    quantidade: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    proposta: Mapped["Proposta"] = relationship(back_populates="itens")
