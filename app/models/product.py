"""Produto e ProdutoPrecoHist — catálogo do módulo Financeiro (RF-PROD).

O produto carrega preço de tabela e piso (preço mínimo). O preço NÃO retroage a
propostas/contratos existentes: cada item grava um snapshot do preço na criação
(RN-F13). Toda alteração de `preco_tabela` gera uma linha em `produto_precos_hist`
(RF-PROD-05). O % de comissão NÃO é atributo do produto (é por perfil do vendedor,
fase seguinte).
"""
import enum
import uuid
from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin, uuid_pk


class ProdutoTipo(str, enum.Enum):
    RECORRENTE = "recorrente"
    PONTUAL = "pontual"


class Produto(Base, TenantMixin, TimestampMixin):
    __tablename__ = "produtos"

    id: Mapped[uuid.UUID] = uuid_pk()
    nome: Mapped[str] = mapped_column(String(160), nullable=False)
    descricao: Mapped[str | None] = mapped_column(Text)
    tipo: Mapped[str] = mapped_column(String(12), nullable=False, default=ProdutoTipo.RECORRENTE.value)
    preco_tabela: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    preco_minimo: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)


class ProdutoPrecoHist(Base, TenantMixin, TimestampMixin):
    __tablename__ = "produto_precos_hist"

    id: Mapped[uuid.UUID] = uuid_pk()
    produto_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("produtos.id"), nullable=False, index=True
    )
    preco_anterior: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    preco_novo: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    usuario_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
