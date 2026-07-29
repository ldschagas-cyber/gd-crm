"""Tenant — empresa cliente do CRM (raiz do isolamento multi-tenant)."""
import enum
import uuid

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, uuid_pk


class TenantStatus(str, enum.Enum):
    ATIVO = "ativo"
    SUSPENSO = "suspenso"
    CANCELADO = "cancelado"


class Tenant(Base, TimestampMixin):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = uuid_pk()
    razao_social: Mapped[str] = mapped_column(String(255), nullable=False)
    nome_fantasia: Mapped[str | None] = mapped_column(String(255))
    cnpj: Mapped[str] = mapped_column(String(14), unique=True, nullable=False)
    plano: Mapped[str] = mapped_column(String(40), nullable=False, default="starter")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=TenantStatus.ATIVO.value)
    config: Mapped[dict | None] = mapped_column(JSONB)
