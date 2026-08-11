"""DTOs de OrigemOption — opções cadastráveis do campo Origem (Empresa/Pesquisa de Leads)."""
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class OrigemOptionCreate(BaseModel):
    nome: str = Field(min_length=1, max_length=80)


class OrigemOptionRead(ORMModel):
    id: UUID
    nome: str
