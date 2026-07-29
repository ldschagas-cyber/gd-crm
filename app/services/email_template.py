"""Serviço de modelos de e-mail."""
import re
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.email_template import EmailTemplate
from app.repositories.email_template import EmailTemplateRepository
from app.schemas.common import PageParams
from app.schemas.email_template import EmailTemplateCreate, EmailTemplateUpdate

VAR_RE = re.compile(r"\{\{(\w+)\}\}")


def _extract_vars(assunto: str, corpo: str) -> list[str]:
    found = VAR_RE.findall(f"{assunto} {corpo}")
    # preserva a primeira ordem de aparição, sem duplicatas
    seen: list[str] = []
    for v in found:
        if v not in seen:
            seen.append(v)
    return seen


class EmailTemplateService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = EmailTemplateRepository(db)

    def list(self, params: PageParams, busca: str | None = None) -> tuple[list[EmailTemplate], int]:
        filters = []
        if busca:
            filters.append(self.repo.search_filter(busca))
        return self.repo.list(*filters, offset=params.offset, limit=params.size, order_by=EmailTemplate.nome)

    def get(self, template_id: UUID) -> EmailTemplate:
        template = self.repo.get(template_id)
        if template is None:
            raise NotFoundError("Modelo de e-mail não encontrado")
        return template

    def create(self, data: EmailTemplateCreate) -> EmailTemplate:
        template = EmailTemplate(
            nome=data.nome, assunto=data.assunto, corpo=data.corpo,
            variaveis_disponiveis=_extract_vars(data.assunto, data.corpo),
        )
        return self.repo.add(template)

    def update(self, template_id: UUID, data: EmailTemplateUpdate) -> EmailTemplate:
        template = self.get(template_id)
        payload = data.model_dump(exclude_unset=True)
        for field, value in payload.items():
            setattr(template, field, value)
        template.variaveis_disponiveis = _extract_vars(template.assunto, template.corpo)
        return self.repo.save(template)

    def delete(self, template_id: UUID) -> None:
        template = self.get(template_id)
        self.repo.delete(template)
