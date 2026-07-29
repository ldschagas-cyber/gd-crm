"""Snippet — bloco de texto curto reutilizável via atalho (§9.6)."""
import uuid

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin, uuid_pk


class Snippet(Base, TenantMixin, TimestampMixin):
    __tablename__ = "snippets"
    __table_args__ = (
        UniqueConstraint("tenant_id", "atalho", name="uq_snippet_tenant_atalho"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    atalho: Mapped[str] = mapped_column(String(40), nullable=False)
    conteudo: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
