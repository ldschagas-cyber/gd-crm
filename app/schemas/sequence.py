"""DTOs de Sequências (RF010)."""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.schemas.common import ORMModel

TIPOS_STEP = {"ligacao", "email", "whatsapp", "linkedin_conexao", "linkedin_mensagem", "tarefa_manual", "followup"}
TIPOS_COM_MESSAGE_TEMPLATE = {"whatsapp", "linkedin_conexao", "linkedin_mensagem"}


class SequenceStepIn(BaseModel):
    dia_offset: int = Field(ge=0)
    tipo: str
    template_id: UUID | None = None  # modelo de e-mail — só quando tipo="email"
    message_template_id: UUID | None = None  # modelo de WhatsApp/LinkedIn
    instrucoes: str | None = None

    @model_validator(mode="after")
    def valida_tipo(self):
        if self.tipo not in TIPOS_STEP:
            raise ValueError(f"Tipo de etapa inválido: {self.tipo}")
        if self.template_id is not None and self.tipo != "email":
            raise ValueError("template_id só é válido para etapas do tipo email")
        if self.message_template_id is not None and self.tipo not in TIPOS_COM_MESSAGE_TEMPLATE:
            raise ValueError(f"message_template_id só é válido para etapas do tipo {sorted(TIPOS_COM_MESSAGE_TEMPLATE)}")
        return self


class SequenceStepRead(ORMModel):
    id: UUID
    ordem: int
    dia_offset: int
    tipo: str
    template_id: UUID | None
    message_template_id: UUID | None
    instrucoes: str | None


class SequenceBase(BaseModel):
    nome: str = Field(min_length=1, max_length=120)
    ativo: bool = True
    pausar_em_resposta: bool = True


class SequenceCreate(SequenceBase):
    steps: list[SequenceStepIn] = Field(min_length=1)


class SequenceUpdate(BaseModel):
    nome: str | None = Field(default=None, min_length=1, max_length=120)
    ativo: bool | None = None
    pausar_em_resposta: bool | None = None
    steps: list[SequenceStepIn] | None = Field(default=None, min_length=1)


class SequenceRead(ORMModel):
    id: UUID
    nome: str
    ativo: bool
    pausar_em_resposta: bool
    created_at: datetime
    steps: list[SequenceStepRead]
    inscritos_ativos: int = 0


class SequenceEnrollmentCreate(BaseModel):
    company_id: UUID | None = None
    contact_id: UUID | None = None
    deal_id: UUID | None = None

    @model_validator(mode="after")
    def valida_alvo(self):
        if not (self.company_id or self.contact_id or self.deal_id):
            raise ValueError("Informe ao menos uma empresa, contato ou negócio para inscrever")
        return self


class SequenceEnrollmentRead(ORMModel):
    id: UUID
    sequence_id: UUID
    company_id: UUID | None
    contact_id: UUID | None
    deal_id: UUID | None
    status: str
    step_atual: int
    pausado_motivo: str | None
    iniciado_em: datetime
    alvo_nome: str
    alvo_tipo: str
