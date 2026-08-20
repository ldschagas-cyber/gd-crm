"""Repositório de metas de venda (SalesTarget)."""
from uuid import UUID

from app.models.sales_target import SalesTarget
from app.repositories.base import BaseRepository


class SalesTargetRepository(BaseRepository[SalesTarget]):
    model = SalesTarget

    def get_by_user_mes(self, user_id: UUID, mes: str) -> SalesTarget | None:
        stmt = self._base_query().where(SalesTarget.user_id == user_id, SalesTarget.mes == mes)
        return self.db.execute(stmt).scalar_one_or_none()
