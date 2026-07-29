"""DTOs de tenant."""
from uuid import UUID

from pydantic import BaseModel

from app.schemas.common import ORMModel


class TenantUpdate(BaseModel):
    razao_social: str | None = None
    nome_fantasia: str | None = None
    plano: str | None = None
    config: dict | None = None


class TenantRead(ORMModel):
    id: UUID
    razao_social: str
    nome_fantasia: str | None
    cnpj: str
    plano: str
    status: str
    config: dict | None
