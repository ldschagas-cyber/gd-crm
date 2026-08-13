"""DTOs do checklist de implantação (Customer Success)."""
from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel

from app.schemas.common import ORMModel


class OnboardingItemRead(ORMModel):
    id: UUID
    company_id: UUID
    titulo: str
    ordem: int
    status: str
    prazo: date | None
    concluido_em: datetime | None
    responsavel_id: UUID | None


class OnboardingItemStatusUpdate(BaseModel):
    status: str  # "pendente" | "concluido"
