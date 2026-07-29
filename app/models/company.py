"""Company — empresas (leads e clientes) do tenant."""
import enum
import uuid

from sqlalchemy import ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SoftDeleteMixin, TenantMixin, TimestampMixin, uuid_pk


class CompanyStatus(str, enum.Enum):
    LEAD = "lead"
    QUALIFICADO = "qualificado"
    CLIENTE = "cliente"
    PERDIDO = "perdido"
    INATIVO = "inativo"


class Company(Base, TenantMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "companies"
    __table_args__ = (
        UniqueConstraint("tenant_id", "cnpj", name="uq_company_tenant_cnpj"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    razao_social: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    nome_fantasia: Mapped[str | None] = mapped_column(String(255))
    cnpj: Mapped[str | None] = mapped_column(String(14))
    site: Mapped[str | None] = mapped_column(String(255))
    telefone: Mapped[str | None] = mapped_column(String(20))
    email: Mapped[str | None] = mapped_column(String(255))
    endereco: Mapped[str | None] = mapped_column(String(255))
    cidade: Mapped[str | None] = mapped_column(String(120))
    uf: Mapped[str | None] = mapped_column(String(2))
    segmento: Mapped[str | None] = mapped_column(String(120))
    porte: Mapped[str | None] = mapped_column(String(40))
    num_funcionarios: Mapped[int | None] = mapped_column(Integer)
    faturamento_estimado: Mapped[float | None] = mapped_column(Numeric(15, 2))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=CompanyStatus.LEAD.value, index=True)
    origem: Mapped[str | None] = mapped_column(String(80))
    responsavel_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    created_by: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
