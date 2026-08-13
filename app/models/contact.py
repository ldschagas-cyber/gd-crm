"""Contact — contatos vinculados a uma empresa."""
import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin, uuid_pk


class Contact(Base, TenantMixin, TimestampMixin):
    __tablename__ = "contacts"

    id: Mapped[uuid.UUID] = uuid_pk()
    company_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True
    )
    # Sempre igual a company.responsavel_id no momento da criação — contato nunca tem
    # dono independente da empresa (trava decidida com o usuário). Por isso não aparece
    # em ContactCreate/ContactUpdate (ver app/schemas/contact.py): é sempre herdado da
    # empresa em ContactService.create, e propagado em cascata por
    # ContactRepository.update_responsavel_for_company quando o responsável da empresa
    # muda (ver CompanyService.update). Nullable só porque contatos criados antes desta
    # coluna existir podem ter empresa sem responsável (ver migração de backfill).
    responsavel_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), index=True
    )
    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    cargo: Mapped[str | None] = mapped_column(String(120))
    email: Mapped[str | None] = mapped_column(String(255))
    telefone: Mapped[str | None] = mapped_column(String(20))
    whatsapp: Mapped[str | None] = mapped_column(String(20))
    linkedin: Mapped[str | None] = mapped_column(String(255))
    data_nascimento: Mapped[date | None] = mapped_column(Date)
    observacoes: Mapped[str | None] = mapped_column(Text)
    contexto_pessoal: Mapped[str | None] = mapped_column(Text)
