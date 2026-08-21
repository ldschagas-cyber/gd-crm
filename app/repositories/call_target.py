"""Repositório de metas de ligações (CallTarget)."""
from uuid import UUID

from app.models.call_target import CallTarget
from app.repositories.base import BaseRepository


class CallTargetRepository(BaseRepository[CallTarget]):
    model = CallTarget

    def get_by_user_mes(self, user_id: UUID, mes: str) -> CallTarget | None:
        stmt = self._base_query().where(CallTarget.user_id == user_id, CallTarget.mes == mes)
        return self.db.execute(stmt).scalar_one_or_none()
