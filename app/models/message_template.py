"""MessageTemplate — modelo de WhatsApp/LinkedIn reutilizável por Sequências.

Irmão de EmailTemplate (app/models/email_template.py), mas sem `assunto`
(mensagem curta não tem campo de assunto) e com `canal` pra diferenciar
WhatsApp de LinkedIn (nota de conexão x mensagem pós-aceite têm contextos de
uso diferentes, cada um mapeado a um SequenceStep.tipo distinto)."""
import uuid

from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin, uuid_pk

CANAIS_MESSAGE_TEMPLATE = {"whatsapp", "linkedin_conexao", "linkedin_mensagem"}


class MessageTemplate(Base, TenantMixin, TimestampMixin):
    __tablename__ = "message_templates"

    id: Mapped[uuid.UUID] = uuid_pk()
    canal: Mapped[str] = mapped_column(String(20), nullable=False)
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    corpo: Mapped[str] = mapped_column(Text, nullable=False)
    variaveis_disponiveis: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    # SID (ex.: "HXxxxxxxxx...") do Content Template cadastrado no Twilio Content
    # Template Builder, ligado a um template de WhatsApp aprovado pela Meta — só
    # canal="whatsapp" usa isso. Enquanto vazio (caso de qualquer template ainda não
    # aprovado), a etapa de Sequência correspondente continua virando Tarefa manual
    # em vez de envio automático — ver app/services/sequence_dispatch.py.
    whatsapp_content_sid: Mapped[str | None] = mapped_column(String(64))
