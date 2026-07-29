"""DTOs de Cadências (RF011)."""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.schemas.common import ORMModel


class CadenceStepIn(BaseModel):
    dias_espera: int = Field(ge=0)
    template_id: UUID


class CadenceStepRead(ORMModel):
    id: UUID
    ordem: int
    dias_espera: int
    template_id: UUID


class CadenceBase(BaseModel):
    nome: str = Field(min_length=1, max_length=120)
    ativo: bool = True
    pausar_em_resposta: bool = True
    criar_followup: bool = False
    followup_titulo: str | None = Field(default=None, max_length=255)


class CadenceCreate(CadenceBase):
    steps: list[CadenceStepIn] = Field(min_length=1)


class CadenceUpdate(BaseModel):
    nome: str | None = Field(default=None, min_length=1, max_length=120)
    ativo: bool | None = None
    pausar_em_resposta: bool | None = None
    criar_followup: bool | None = None
    followup_titulo: str | None = Field(default=None, max_length=255)
    steps: list[CadenceStepIn] | None = Field(default=None, min_length=1)


class CadenceRead(ORMModel):
    id: UUID
    nome: str
    ativo: bool
    pausar_em_resposta: bool
    criar_followup: bool
    followup_titulo: str | None
    created_at: datetime
    steps: list[CadenceStepRead]
    inscritos_ativos: int = 0


class CadenceEnrollmentCreate(BaseModel):
    company_id: UUID | None = None
    contact_id: UUID | None = None
    deal_id: UUID | None = None

    @model_validator(mode="after")
    def valida_alvo(self):
        if not (self.company_id or self.contact_id or self.deal_id):
            raise ValueError("Informe ao menos uma empresa, contato ou negócio para inscrever")
        return self


class CadenceEnrollmentRead(ORMModel):
    id: UUID
    cadence_id: UUID
    company_id: UUID | None
    contact_id: UUID | None
    deal_id: UUID | None
    status: str
    step_atual: int
    pausado_motivo: str | None
    iniciado_em: datetime
    alvo_nome: str
    alvo_tipo: str
