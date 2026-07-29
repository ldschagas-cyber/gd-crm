"""Repositório de modelos de e-mail."""
from sqlalchemy import or_

from app.models.email_template import EmailTemplate
from app.repositories.base import BaseRepository


class EmailTemplateRepository(BaseRepository[EmailTemplate]):
    model = EmailTemplate

    def search_filter(self, termo: str):
        like = f"%{termo}%"
        return or_(EmailTemplate.nome.ilike(like), EmailTemplate.assunto.ilike(like))
