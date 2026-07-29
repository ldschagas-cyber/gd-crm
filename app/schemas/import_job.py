"""DTOs de job de importação."""
from datetime import datetime
from uuid import UUID

from app.schemas.common import ORMModel


class ImportJobRead(ORMModel):
    id: UUID
    tipo: str
    arquivo: str
    status: str
    total_linhas: int | None
    importadas: int | None
    erros: list | None
    created_at: datetime
