"""DTOs de usuário."""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.models.user import UserRole, UserStatus
from app.schemas.common import ORMModel


class UserCreate(BaseModel):
    nome: str = Field(min_length=1, max_length=255)
    email: EmailStr
    senha: str = Field(min_length=8)
    telefone: str | None = None
    cargo: str | None = None
    perfil: UserRole = UserRole.VENDEDOR
    meta_pesquisa_semanal: int | None = Field(default=None, ge=0)
    meta_pesquisa_mensal: int | None = Field(default=None, ge=0)


class UserUpdate(BaseModel):
    nome: str | None = None
    telefone: str | None = None
    cargo: str | None = None
    perfil: UserRole | None = None
    meta_pesquisa_semanal: int | None = Field(default=None, ge=0)
    meta_pesquisa_mensal: int | None = Field(default=None, ge=0)


class UserStatusUpdate(BaseModel):
    status: UserStatus


class UserRead(ORMModel):
    id: UUID
    nome: str
    email: EmailStr
    telefone: str | None
    cargo: str | None
    perfil: str
    status: str
    ultimo_acesso: datetime | None
    created_at: datetime
    avatar_url: str | None
    meta_pesquisa_semanal: int | None
    meta_pesquisa_mensal: int | None
