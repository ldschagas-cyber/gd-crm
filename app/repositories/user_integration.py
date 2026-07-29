"""Repositório de integrações pessoais (e-mail/calendário)."""
from uuid import UUID

from app.models.user_integration import UserIntegration
from app.repositories.base import BaseRepository


class UserIntegrationRepository(BaseRepository[UserIntegration]):
    model = UserIntegration

    def get_by_user_tipo(self, user_id: UUID, tipo: str) -> UserIntegration | None:
        return self.db.execute(
            self._base_query().where(
                UserIntegration.user_id == user_id, UserIntegration.tipo == tipo,
            )
        ).scalar_one_or_none()
