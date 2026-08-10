"""DTOs de pipeline e etapas."""
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.pipeline import FunilMarco, StageColorMode, StageType
from app.schemas.common import ORMModel


class StageCreate(BaseModel):
    nome: str = Field(min_length=1, max_length=120)
    ordem: int = 0
    tipo: StageType = StageType.ABERTA
    sla_horas: int | None = None
    probabilidade: int | None = Field(default=None, ge=0, le=100)
    # Marca esta etapa como o "Diagnóstico"/"Proposta" do funil de metas (Anexo 1 —
    # ver docs/PLANO_METAS_FUNIL.md). Opcional, nenhuma etapa nasce marcada.
    marco_funil: FunilMarco | None = None


class StageRead(ORMModel):
    id: UUID
    pipeline_id: UUID
    nome: str
    ordem: int
    tipo: str
    sla_horas: int | None
    probabilidade: int | None
    marco_funil: str | None


class PipelineCreate(BaseModel):
    nome: str = Field(min_length=1, max_length=120)
    is_default: bool = False
    cor_exibicao: StageColorMode = StageColorMode.SEM_COR
    stages: list[StageCreate] = []


class PipelineUpdate(BaseModel):
    nome: str | None = None
    is_default: bool | None = None
    ativo: bool | None = None
    cor_exibicao: StageColorMode | None = None


class PipelineRead(ORMModel):
    id: UUID
    nome: str
    is_default: bool
    ativo: bool
    cor_exibicao: str
    stages: list[StageRead] = []


class BoardColumn(BaseModel):
    stage: StageRead
    deals: list["DealRead"]


class BoardResponse(BaseModel):
    pipeline_id: UUID
    columns: list[BoardColumn]
