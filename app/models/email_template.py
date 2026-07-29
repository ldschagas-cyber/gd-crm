"""EmailTemplate — modelo de e-mail reutilizável por Sequências/Cadências (§9.5/§9)."""
import uuid

from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin, uuid_pk


class EmailTemplate(Base, TenantMixin, TimestampMixin):
    __tablename__ = "email_templates"

    id: Mapped[uuid.UUID] = uuid_pk()
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    assunto: Mapped[str] = mapped_column(String(255), nullable=False)
    corpo: Mapped[str] = mapped_column(Text, nullable=False)
    variaveis_disponiveis: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
