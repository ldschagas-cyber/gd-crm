"""Repositório de negócios."""
from uuid import UUID

from app.models.deal import Deal
from app.repositories.base import BaseRepository


class DealRepository(BaseRepository[Deal]):
    model = Deal

    def search_filter(self, termo: str):
        return Deal.nome.ilike(f"%{termo}%")

    def list_by_stage(self, stage_id: UUID) -> list[Deal]:
        items, _ = self.list(Deal.stage_id == stage_id, limit=1000, order_by=Deal.created_at)
        return items
