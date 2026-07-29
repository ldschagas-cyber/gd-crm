"""Schemas de Formulários (item 9.8 — captura de leads no site institucional)."""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.models.form import FORM_FIELD_LIBRARY, FormStatus, PostSubmitAction


def _valida_campos(campos: list[str], campos_personalizados: dict[str, str]) -> None:
    invalidos = [c for c in campos if c not in FORM_FIELD_LIBRARY and c not in campos_personalizados]
    if invalidos:
        raise ValueError(f"Campos desconhecidos: {invalidos}")


class FormCreate(BaseModel):
    nome: str = Field(min_length=1, max_length=255)
    pagina: str | None = None
    status: FormStatus = FormStatus.RASCUNHO
    campos: list[str] = []
    campos_personalizados: dict[str, str] = {}
    post_submit_action: PostSubmitAction = PostSubmitAction.CRIAR_LEAD

    @model_validator(mode="after")
    def _checa_campos(self) -> "FormCreate":
        _valida_campos(self.campos, self.campos_personalizados)
        return self


class FormUpdate(BaseModel):
    nome: str | None = Field(default=None, min_length=1, max_length=255)
    pagina: str | None = None
    status: FormStatus | None = None
    campos: list[str] | None = None
    campos_personalizados: dict[str, str] | None = None
    post_submit_action: PostSubmitAction | None = None

    @model_validator(mode="after")
    def _checa_campos(self) -> "FormUpdate":
        if self.campos is not None:
            _valida_campos(self.campos, self.campos_personalizados or {})
        return self


class FormRead(BaseModel):
    id: UUID
    nome: str
    pagina: str | None
    status: str
    campos: list[str]
    campos_personalizados: dict[str, str]
    post_submit_action: str
    created_at: datetime
    updated_at: datetime
    envios_30d: int
    conversao_pct: float | None


class FormSubmissionRead(BaseModel):
    id: UUID
    form_id: UUID
    nome: str
    email: str
    valores: dict
    company_id: UUID | None
    contact_id: UUID | None
    duplicado: bool
    created_at: datetime


class FormKpis(BaseModel):
    formularios_ativos: int
    formularios_total: int
    envios_30d: int
    taxa_conversao_media: float | None
    leads_gerados_30d: int


class PublicFormSubmit(BaseModel):
    """Payload enviado pelo widget público — só nome/e-mail são sempre obrigatórios,
    o resto depende de quais campos o formulário tem configurados."""
    nome: str = Field(min_length=1, max_length=255)
    email: str = Field(min_length=1, max_length=255)
    valores: dict = {}
