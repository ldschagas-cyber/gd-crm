"""DTOs de timeline."""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.timeline import TimelineType
from app.schemas.common import ORMModel


class TimelineNoteCreate(BaseModel):
    titulo: str = Field(min_length=1, max_length=255)
    descricao: str | None = None
    tipo: TimelineType = TimelineType.NOTA
    deal_id: UUID | None = None
    contact_id: UUID | None = None
    # tipo=email: se informado, despacha de verdade via Microsoft Graph (Mail.Send)
    # em vez de só registrar uma nota manual.
    destinatario: str | None = None
    # tipo=reuniao: se informados, cria o evento de verdade na agenda Outlook
    # conectada (e, com criar_teams, uma reunião do Teams dentro dele).
    inicio: datetime | None = None
    fim: datetime | None = None
    criar_teams: bool = False


class TimelineEventRead(ORMModel):
    id: UUID
    company_id: UUID
    deal_id: UUID | None
    contact_id: UUID | None
    tipo: str
    titulo: str
    descricao: str | None
    evento_meta: dict | None
    user_id: UUID | None
    created_at: datetime
