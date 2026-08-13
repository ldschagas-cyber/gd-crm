"""Repositório de itens do checklist de implantação (Customer Success)."""
from uuid import UUID

from app.models.onboarding import OnboardingChecklistItem
from app.repositories.base import BaseRepository


class OnboardingChecklistItemRepository(BaseRepository[OnboardingChecklistItem]):
    model = OnboardingChecklistItem

    def list_by_company(self, company_id: UUID) -> list[OnboardingChecklistItem]:
        items, _ = self.list(
            OnboardingChecklistItem.company_id == company_id,
            limit=200, order_by=OnboardingChecklistItem.ordem,
        )
        return items
