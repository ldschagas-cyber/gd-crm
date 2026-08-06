"""User — usuário operador do CRM."""
import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin, uuid_pk


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    GESTOR = "gestor"
    VENDEDOR = "vendedor"
    VISUALIZADOR = "visualizador"


class UserStatus(str, enum.Enum):
    ATIVO = "ativo"
    INATIVO = "inativo"


class User(Base, TenantMixin, TimestampMixin):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("tenant_id", "email", name="uq_user_tenant_email"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    senha_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    telefone: Mapped[str | None] = mapped_column(String(20))
    cargo: Mapped[str | None] = mapped_column(String(120))
    perfil: Mapped[str] = mapped_column(String(30), nullable=False, default=UserRole.VENDEDOR.value)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=UserStatus.ATIVO.value)
    ultimo_acesso: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    avatar_url: Mapped[str | None] = mapped_column(String(500))

    # Meta de pesquisa (Pesquisa de Leads) — individual por usuário, usada só pra
    # calcular o progresso exibido em Desempenho > Metas de pesquisa. None = sem
    # meta definida (o usuário some da seção de metas se também não tiver pesquisado nada).
    meta_pesquisa_semanal: Mapped[int | None] = mapped_column(Integer)
    meta_pesquisa_mensal: Mapped[int | None] = mapped_column(Integer)
