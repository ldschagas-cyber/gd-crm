"""DTOs de contato."""
from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class ContactCreate(BaseModel):
    company_id: UUID
    nome: str = Field(min_length=1, max_length=255)
    cargo: str | None = None
    email: str | None = None
    telefone: str | None = None
    whatsapp: str | None = None
    linkedin: str | None = None
    data_nascimento: date | None = None
    observacoes: str | None = None
    contexto_pessoal: str | None = None


class ContactUpdate(BaseModel):
    nome: str | None = None
    cargo: str | None = None
    email: str | None = None
    telefone: str | None = None
    whatsapp: str | None = None
    linkedin: str | None = None
    data_nascimento: date | None = None
    observacoes: str | None = None
    contexto_pessoal: str | None = None


class ContactRead(ORMModel):
    id: UUID
    company_id: UUID
    nome: str
    cargo: str | None
    email: str | None
    telefone: str | None
    whatsapp: str | None
    linkedin: str | None
    data_nascimento: date | None
    observacoes: str | None
    contexto_pessoal: str | None
    created_at: datetime


class ContactFilterOptions(BaseModel):
    """Valores distintos de cargo já cadastrados (cargo é texto livre no cadastro)."""
    cargo: list[str] = []


class ContactEmailRead(BaseModel):
    assunto: str
    resumo: str
    quando: datetime | None
    direcao: str  # "enviado" | "recebido"
