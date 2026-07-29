"""Repositório de eventos de timeline."""
from uuid import UUID

from app.models.timeline import TimelineEvent
from app.repositories.base import BaseRepository


class TimelineRepository(BaseRepository[TimelineEvent]):
    model = TimelineEvent

    def list_by_company(self, company_id: UUID, offset: int, limit: int) -> tuple[list[TimelineEvent], int]:
        return self.list(
            TimelineEvent.company_id == company_id,
            offset=offset,
            limit=limit,
            order_by=TimelineEvent.created_at.desc(),
        )

    def list_by_deal(self, deal_id: UUID, offset: int, limit: int) -> tuple[list[TimelineEvent], int]:
        return self.list(
            TimelineEvent.deal_id == deal_id,
            offset=offset,
            limit=limit,
            order_by=TimelineEvent.created_at.desc(),
        )
