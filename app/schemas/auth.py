"""DTOs de autenticação."""
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import ORMModel


class LoginRequest(BaseModel):
    email: EmailStr
    senha: str = Field(min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    nova_senha: str = Field(min_length=8)


class MeResponse(ORMModel):
    id: UUID
    tenant_id: UUID
    nome: str
    email: EmailStr
    telefone: str | None
    cargo: str | None
    perfil: str
    status: str
    avatar_url: str | None
