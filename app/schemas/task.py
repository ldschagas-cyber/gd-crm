"""DTOs de tarefa."""
from datetime import date, datetime, time
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.task import TaskPriority, TaskStatus, TaskType
from app.schemas.common import ORMModel


class TaskCreate(BaseModel):
    titulo: str = Field(min_length=1, max_length=255)
    descricao: str | None = None
    tipo: TaskType
    responsavel_id: UUID
    company_id: UUID | None = None
    contact_id: UUID | None = None
    deal_id: UUID | None = None
    data: date
    hora: time | None = None
    prioridade: TaskPriority = TaskPriority.MEDIA


class TaskUpdate(BaseModel):
    titulo: str | None = None
    descricao: str | None = None
    tipo: TaskType | None = None
    responsavel_id: UUID | None = None
    company_id: UUID | None = None
    contact_id: UUID | None = None
    deal_id: UUID | None = None
    data: date | None = None
    hora: time | None = None
    prioridade: TaskPriority | None = None
    status: TaskStatus | None = None


class TaskRead(ORMModel):
    id: UUID
    titulo: str
    descricao: str | None
    tipo: str
    responsavel_id: UUID
    company_id: UUID | None
    contact_id: UUID | None
    deal_id: UUID | None
    data: date
    hora: time | None
    prioridade: str
    status: str
    concluida_em: datetime | None
    created_at: datetime
