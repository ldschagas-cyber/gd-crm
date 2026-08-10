"""DTOs de tarefa."""
from datetime import date, datetime, time
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.models.task import ResultadoLigacao, TaskPriority, TaskStatus, TaskType
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
    resultado_ligacao: str | None
    created_at: datetime


class TaskComplete(BaseModel):
    """Corpo opcional do PATCH /tasks/{id}/complete — só faz sentido preencher
    `resultado_ligacao`/`observacoes` quando a tarefa é de ligação (fila de
    execução); demais tipos simplesmente concluem sem body."""
    resultado_ligacao: ResultadoLigacao | None = None
    observacoes: str | None = None


class TaskSendEmail(BaseModel):
    """Corpo do POST /tasks/{id}/send-email — envio manual pela fila de
    execução, via a mesma integração Microsoft 365 (Graph) já usada pelo envio
    automático de Sequências. Exige que o responsável tenha a integração
    'email' conectada e ativa em Preferências (senão a Graph recusa e o
    endpoint devolve 409 — o painel da fila deve checar isso antes e oferecer
    o fallback mailto: em vez de tentar)."""
    destinatario: EmailStr
    assunto: str = Field(min_length=1, max_length=255)
    corpo: str = Field(min_length=1)
