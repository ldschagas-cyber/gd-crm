"""DTOs de Modelo de mensagem (WhatsApp/LinkedIn)."""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.models.message_template import CANAIS_MESSAGE_TEMPLATE
from app.schemas.common import ORMModel


def _valida_canal(v: str) -> str:
    if v not in CANAIS_MESSAGE_TEMPLATE:
        raise ValueError(f"Canal inválido: {v}")
    return v


class MessageTemplateBase(BaseModel):
    canal: str
    nome: str = Field(min_length=1, max_length=120)
    corpo: str = Field(min_length=1)
    # Só usado em canal="whatsapp" — SID do Content Template aprovado pela Meta
    # via Twilio (ver app/models/message_template.py). Opcional em qualquer canal.
    whatsapp_content_sid: str | None = Field(default=None, max_length=64)

    _valida_canal = field_validator("canal")(_valida_canal)


class MessageTemplateCreate(MessageTemplateBase):
    pass


class MessageTemplateUpdate(BaseModel):
    canal: str | None = None
    nome: str | None = Field(default=None, min_length=1, max_length=120)
    corpo: str | None = Field(default=None, min_length=1)
    whatsapp_content_sid: str | None = Field(default=None, max_length=64)

    @field_validator("canal")
    @classmethod
    def _valida_canal_opcional(cls, v: str | None) -> str | None:
        if v is not None:
            _valida_canal(v)
        return v


class MessageTemplateRead(ORMModel):
    id: UUID
    canal: str
    nome: str
    corpo: str
    variaveis_disponiveis: list[str]
    whatsapp_content_sid: str | None
    created_at: datetime
