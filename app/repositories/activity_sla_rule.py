"""Repositório de regras de SLA Comercial."""
from uuid import UUID

from app.models.activity_sla_rule import ActivitySlaMilestoneHit, ActivitySlaRule
from app.repositories.base import BaseRepository


class ActivitySlaRuleRepository(BaseRepository[ActivitySlaRule]):
    model = ActivitySlaRule


class ActivitySlaMilestoneHitRepository(BaseRepository[ActivitySlaMilestoneHit]):
    model = ActivitySlaMilestoneHit

    def get_by_rule_and_companies(self, rule_ids: list[UUID], company_ids: list[UUID]
                                  ) -> list[ActivitySlaMilestoneHit]:
        if not rule_ids or not company_ids:
            return []
        items, _ = self.list(
            ActivitySlaMilestoneHit.rule_id.in_(rule_ids),
            ActivitySlaMilestoneHit.company_id.in_(company_ids),
            limit=10_000,
        )
        return items
