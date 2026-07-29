"""DTOs de Snippet."""
import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import ORMModel

ATALHO_RE = re.compile(r"^[a-z0-9]+$")


class SnippetBase(BaseModel):
    nome: str = Field(min_length=1, max_length=120)
    atalho: str = Field(min_length=1, max_length=40)
    conteudo: str = Field(min_length=1)

    @field_validator("atalho")
    @classmethod
    def valida_atalho(cls, v: str) -> str:
        v = v.strip().lower()
        if not ATALHO_RE.match(v):
            raise ValueError("Atalho deve conter só letras minúsculas e números, sem espaço")
        return v


class SnippetCreate(SnippetBase):
    pass


class SnippetUpdate(BaseModel):
    nome: str | None = Field(default=None, min_length=1, max_length=120)
    atalho: str | None = Field(default=None, min_length=1, max_length=40)
    conteudo: str | None = Field(default=None, min_length=1)

    @field_validator("atalho")
    @classmethod
    def valida_atalho(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip().lower()
        if not ATALHO_RE.match(v):
            raise ValueError("Atalho deve conter só letras minúsculas e números, sem espaço")
        return v


class SnippetRead(ORMModel):
    id: UUID
    nome: str
    atalho: str
    conteudo: str
    created_by: UUID | None
    created_at: datetime
