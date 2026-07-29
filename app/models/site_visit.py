"""SiteVisit — rastreio de visitas ao site institucional (item 9.8), com identificação
opcional de empresa por IP corporativo via provedor externo (IPinfo)."""
import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin, uuid_pk


class SiteVisit(Base, TenantMixin, TimestampMixin):
    __tablename__ = "site_visits"

    id: Mapped[uuid.UUID] = uuid_pk()
    session_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    path: Mapped[str] = mapped_column(String(500), nullable=False)
    referrer: Mapped[str | None] = mapped_column(String(500))
    origem: Mapped[str | None] = mapped_column(String(80))  # classificação: Direto/Google orgânico/E-mail/etc.
    ip: Mapped[str | None] = mapped_column(String(45))
    empresa_identificada: Mapped[str | None] = mapped_column(String(255))  # nome cru devolvido pelo provedor de IP
    company_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("companies.id"))
