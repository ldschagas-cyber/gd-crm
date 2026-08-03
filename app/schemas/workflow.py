"""DTOs de Workflows (RF018)."""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.schemas.common import ORMModel

GATILHOS = {"empresa_criada", "contato_criado", "negocio_criado", "mudanca_etapa", "resposta_recebida"}
TIPOS_ACAO = {
    "criar_tarefa", "enviar_email", "alterar_pipeline", "notificar_usuario",
    "executar_enriquecimento", "inscrever_em_sequencia",
}


class WorkflowCondition(BaseModel):
    campo: str
    operador: str
    valor: str


class WorkflowActionIn(BaseModel):
    tipo_acao: str
    parametros: dict = Field(default_factory=dict)

    @model_validator(mode="after")
    def valida_tipo(self):
        if self.tipo_acao not in TIPOS_ACAO:
            raise ValueError(f"Tipo de ação inválido: {self.tipo_acao}")
        return self


class WorkflowActionRead(ORMModel):
    id: UUID
    ordem: int
    tipo_acao: str
    parametros: dict


class WorkflowBase(BaseModel):
    nome: str = Field(min_length=1, max_length=120)
    gatilho: str
    condicoes: list[WorkflowCondition] = Field(default_factory=list)
    ativo: bool = True

    @model_validator(mode="after")
    def valida_gatilho(self):
        if self.gatilho not in GATILHOS:
            raise ValueError(f"Gatilho inválido: {self.gatilho}")
        return self


class WorkflowCreate(WorkflowBase):
    actions: list[WorkflowActionIn] = Field(min_length=1)


class WorkflowUpdate(BaseModel):
    nome: str | None = Field(default=None, min_length=1, max_length=120)
    gatilho: str | None = None
    condicoes: list[WorkflowCondition] | None = None
    ativo: bool | None = None
    actions: list[WorkflowActionIn] | None = Field(default=None, min_length=1)


class WorkflowRead(ORMModel):
    id: UUID
    nome: str
    gatilho: str
    condicoes: list[WorkflowCondition]
    ativo: bool
    created_at: datetime
    actions: list[WorkflowActionRead]


class WorkflowExecutionLogRead(ORMModel):
    id: UUID
    workflow_id: UUID | None
    entidade_ref: UUID
    resultado: str
    detalhes: dict | None
    executado_em: datetime
