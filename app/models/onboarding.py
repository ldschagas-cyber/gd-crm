"""OnboardingChecklistItem — checklist de implantação do Customer Success.

Criado automaticamente (a partir de um template por tenant, ver
app/services/onboarding.py) quando uma empresa entra na fase `implantacao`
(CsFase.IMPLANTACAO). Ver docs/PLANO_CUSTOMER_SUCCESS.md §2.
"""
import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin, uuid_pk


class OnboardingItemStatus(str, enum.Enum):
    PENDENTE = "pendente"
    CONCLUIDO = "concluido"


class OnboardingChecklistItem(Base, TenantMixin, TimestampMixin):
    __tablename__ = "onboarding_checklist_items"

    id: Mapped[uuid.UUID] = uuid_pk()
    company_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True
    )
    titulo: Mapped[str] = mapped_column(String(255), nullable=False)
    ordem: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=OnboardingItemStatus.PENDENTE.value)
    prazo: Mapped[date | None] = mapped_column(Date)
    concluido_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    responsavel_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
