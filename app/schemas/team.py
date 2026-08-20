"""DTOs de equipe de vendas."""
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class TeamCreate(BaseModel):
    nome: str = Field(min_length=1, max_length=120)
    gestor_id: UUID | None = None


class TeamUpdate(BaseModel):
    nome: str | None = Field(default=None, min_length=1, max_length=120)
    gestor_id: UUID | None = None


class TeamRead(ORMModel):
    id: UUID
    nome: str
    gestor_id: UUID | None
