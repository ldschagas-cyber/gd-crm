"""DTOs de Preferências pessoais (auto-atendimento do próprio usuário)."""
from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class MeUpdate(BaseModel):
    nome: str | None = Field(default=None, min_length=1, max_length=255)
    telefone: str | None = None
    cargo: str | None = None


class PasswordChange(BaseModel):
    senha_atual: str = Field(min_length=1)
    senha_nova: str = Field(min_length=8)


class IntegrationRead(BaseModel):
    tipo: str
    provider: str
    conectado: bool
    conectado_em: datetime | None
    ativo: bool


class IntegrationStatus(BaseModel):
    disponivel: bool
    motivo: str | None = None


class IntegrationAuthorizeUrl(BaseModel):
    auth_url: str


class UpcomingMeetingRead(BaseModel):
    assunto: str
    inicio: datetime
    fim: datetime
    teams_join_url: str | None
