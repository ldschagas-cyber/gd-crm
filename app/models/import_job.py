"""ImportJob — controle de importações Excel/CSV (assíncronas)."""
import enum
import uuid

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin, uuid_pk


class ImportType(str, enum.Enum):
    EMPRESAS = "empresas"
    CONTATOS = "contatos"
    LEAD_PROSPECTS = "lead_prospects"


class ImportStatus(str, enum.Enum):
    PENDENTE = "pendente"
    PROCESSANDO = "processando"
    CONCLUIDO = "concluido"
    ERRO = "erro"


class ImportJob(Base, TenantMixin, TimestampMixin):
    __tablename__ = "import_jobs"

    id: Mapped[uuid.UUID] = uuid_pk()
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)
    arquivo: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=ImportStatus.PENDENTE.value)
    total_linhas: Mapped[int | None] = mapped_column(Integer)
    importadas: Mapped[int | None] = mapped_column(Integer)
    erros: Mapped[list | None] = mapped_column(JSONB)
    created_by: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
