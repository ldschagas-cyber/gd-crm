"""DTOs de negócio."""
from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.deal import DealStatus
from app.schemas.common import ORMModel


class DealCreate(BaseModel):
    nome: str = Field(min_length=1, max_length=255)
    company_id: UUID
    contact_id: UUID | None = None
    responsavel_id: UUID
    pipeline_id: UUID
    stage_id: UUID
    valor_previsto: float | None = None
    probabilidade: int | None = Field(default=None, ge=0, le=100)
    data_prev_fechamento: date | None = None
    # Sem `origem` aqui de propósito — o negócio herda a origem da empresa na criação
    # (ver DealService.create), não é escolhida manualmente.


class DealUpdate(BaseModel):
    nome: str | None = None
    contact_id: UUID | None = None
    responsavel_id: UUID | None = None
    valor_previsto: float | None = None
    probabilidade: int | None = Field(default=None, ge=0, le=100)
    data_prev_fechamento: date | None = None


class DealStageMove(BaseModel):
    stage_id: UUID


class DealClose(BaseModel):
    status: DealStatus
    motivo_perda: str | None = None


class DealRead(ORMModel):
    id: UUID
    nome: str
    company_id: UUID
    contact_id: UUID | None
    responsavel_id: UUID
    pipeline_id: UUID
    stage_id: UUID
    valor_previsto: float | None
    probabilidade: int | None
    data_prev_fechamento: date | None
    origem: str | None
    status: str
    motivo_perda: str | None
    data_fechamento: datetime | None
    created_at: datetime
    ultima_interacao: datetime
