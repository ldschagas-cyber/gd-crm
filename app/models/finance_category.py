"""CategoriaFinanceira — plano de categorias (RF-CAT).

Fase 1 revisada usa só `receita` (categorias de despesa entram com o Contas a Pagar).
O campo `tipo` já existe para não exigir migração quando o Contas a Pagar chegar.
Categorias-padrão são pré-carregadas por tenant (seed no primeiro uso do módulo).
"""
import enum
import uuid

from sqlalchemy import Boolean, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin, uuid_pk


class CategoriaTipo(str, enum.Enum):
    RECEITA = "receita"
    DESPESA = "despesa"  # reservado para o Contas a Pagar (fase seguinte)


class CategoriaFinanceira(Base, TenantMixin, TimestampMixin):
    __tablename__ = "categorias_financeiras"
    __table_args__ = (
        UniqueConstraint("tenant_id", "tipo", "nome", name="uq_categoria_tenant_tipo_nome"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    nome: Mapped[str] = mapped_column(String(80), nullable=False)
    tipo: Mapped[str] = mapped_column(String(8), nullable=False, default=CategoriaTipo.RECEITA.value, index=True)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
