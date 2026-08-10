"""Repositório de modelos de mensagem (WhatsApp/LinkedIn)."""
from sqlalchemy import or_

from app.models.message_template import MessageTemplate
from app.repositories.base import BaseRepository


class MessageTemplateRepository(BaseRepository[MessageTemplate]):
    model = MessageTemplate

    def search_filter(self, termo: str):
        like = f"%{termo}%"
        return or_(MessageTemplate.nome.ilike(like), MessageTemplate.corpo.ilike(like))
