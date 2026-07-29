"""AuditLog — registro de auditoria de operações críticas."""
import enum
import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin, uuid_pk


class AuditAction(str, enum.Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"


class AuditLog(Base, TenantMixin, TimestampMixin):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    entidade: Mapped[str] = mapped_column(String(40), nullable=False)
    entidade_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True))
    acao: Mapped[str] = mapped_column(String(20), nullable=False)
    diff: Mapped[dict | None] = mapped_column(JSONB)
    ip: Mapped[str | None] = mapped_column(String(45))
