"""Repositórios de Formulários e envios."""
from uuid import UUID

from sqlalchemy import select

from app.models.form import Form, FormSubmission
from app.repositories.base import BaseRepository


class FormRepository(BaseRepository[Form]):
    model = Form

    def get_public(self, form_id: UUID) -> Form | None:
        """Busca sem filtro de tenant — usada pelo endpoint público de envio,
        que ainda não tem contexto de tenant (não há JWT). O próprio ID do
        formulário é a capability; o tenant é extraído do resultado."""
        return self.db.execute(select(Form).where(Form.id == form_id)).scalar_one_or_none()


class FormSubmissionRepository(BaseRepository[FormSubmission]):
    model = FormSubmission

    def list_by_form(self, form_id: UUID, offset: int, limit: int) -> tuple[list[FormSubmission], int]:
        return self.list(
            FormSubmission.form_id == form_id,
            offset=offset, limit=limit,
            order_by=FormSubmission.created_at.desc(),
        )
