"""UserIntegration — conexões pessoais de e-mail/calendário (Microsoft 365/Graph).

Tokens ficam em texto puro por ora porque nenhuma integração real (OAuth) foi
configurada ainda — ver Preferências §9.2 da especificação. Antes de gravar um
token de verdade, essas colunas precisam passar a ser criptografadas em repouso.
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin, uuid_pk


class IntegrationType(str, enum.Enum):
    EMAIL = "email"
    CALENDARIO = "calendario"


class UserIntegration(Base, TenantMixin, TimestampMixin):
    __tablename__ = "user_integrations"
    __table_args__ = (
        UniqueConstraint("user_id", "tipo", name="uq_user_integration_user_tipo"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(20), nullable=False, default="microsoft365")
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)
    access_token_enc: Mapped[str | None] = mapped_column(Text)
    refresh_token_enc: Mapped[str | None] = mapped_column(Text)
    conectado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
