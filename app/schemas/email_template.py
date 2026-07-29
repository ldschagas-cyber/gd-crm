"""DTOs de Modelo de e-mail."""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class EmailTemplateBase(BaseModel):
    nome: str = Field(min_length=1, max_length=120)
    assunto: str = Field(min_length=1, max_length=255)
    corpo: str = Field(min_length=1)


class EmailTemplateCreate(EmailTemplateBase):
    pass


class EmailTemplateUpdate(BaseModel):
    nome: str | None = Field(default=None, min_length=1, max_length=120)
    assunto: str | None = Field(default=None, min_length=1, max_length=255)
    corpo: str | None = Field(default=None, min_length=1)


class EmailTemplateRead(ORMModel):
    id: UUID
    nome: str
    assunto: str
    corpo: str
    variaveis_disponiveis: list[str]
    created_at: datetime
