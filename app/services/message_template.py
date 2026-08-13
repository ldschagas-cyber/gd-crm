"""Serviço de modelos de mensagem (WhatsApp/LinkedIn)."""
import re
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.message_template import MessageTemplate
from app.repositories.message_template import MessageTemplateRepository
from app.schemas.common import PageParams
from app.schemas.message_template import MessageTemplateCreate, MessageTemplateUpdate

VAR_RE = re.compile(r"\{\{(\w+)\}\}")


def _extract_vars(corpo: str) -> list[str]:
    found = VAR_RE.findall(corpo)
    # preserva a primeira ordem de aparição, sem duplicatas
    seen: list[str] = []
    for v in found:
        if v not in seen:
            seen.append(v)
    return seen


class MessageTemplateService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = MessageTemplateRepository(db)

    def list(self, params: PageParams, busca: str | None = None,
             canal: str | None = None) -> tuple[list[MessageTemplate], int]:
        filters = []
        if busca:
            filters.append(self.repo.search_filter(busca))
        if canal:
            filters.append(MessageTemplate.canal == canal)
        return self.repo.list(*filters, offset=params.offset, limit=params.size, order_by=MessageTemplate.nome)

    def get(self, template_id: UUID) -> MessageTemplate:
        template = self.repo.get(template_id)
        if template is None:
            raise NotFoundError("Modelo de mensagem não encontrado")
        return template

    def create(self, data: MessageTemplateCreate) -> MessageTemplate:
        template = MessageTemplate(
            canal=data.canal, nome=data.nome, corpo=data.corpo,
            whatsapp_content_sid=data.whatsapp_content_sid,
            variaveis_disponiveis=_extract_vars(data.corpo),
        )
        return self.repo.add(template)

    def update(self, template_id: UUID, data: MessageTemplateUpdate) -> MessageTemplate:
        template = self.get(template_id)
        payload = data.model_dump(exclude_unset=True)
        for field, value in payload.items():
            setattr(template, field, value)
        template.variaveis_disponiveis = _extract_vars(template.corpo)
        return self.repo.save(template)

    def delete(self, template_id: UUID) -> None:
        template = self.get(template_id)
        self.repo.delete(template)
