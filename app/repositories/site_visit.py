"""Repositório de visitas ao site."""
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select

from app.models.site_visit import SiteVisit
from app.repositories.base import BaseRepository


class SiteVisitRepository(BaseRepository[SiteVisit]):
    model = SiteVisit

    def count_by_path_since(self, path: str, since: datetime) -> int:
        stmt = select(func.count()).select_from(
            self._base_query().where(SiteVisit.path == path, SiteVisit.created_at >= since).subquery()
        )
        return self.db.execute(stmt).scalar_one()

    def sessions_per_day(self, since: datetime) -> list[tuple[str, int]]:
        stmt = (
            select(func.date(SiteVisit.created_at), func.count(func.distinct(SiteVisit.session_id)))
            .where(SiteVisit.tenant_id == self._tenant_id(), SiteVisit.created_at >= since)
            .group_by(func.date(SiteVisit.created_at))
            .order_by(func.date(SiteVisit.created_at))
        )
        return [(str(dia), total) for dia, total in self.db.execute(stmt).all()]

    def top_pages(self, since: datetime, limit: int = 10) -> list[tuple[str, int]]:
        stmt = (
            select(SiteVisit.path, func.count())
            .where(SiteVisit.tenant_id == self._tenant_id(), SiteVisit.created_at >= since)
            .group_by(SiteVisit.path)
            .order_by(func.count().desc())
            .limit(limit)
        )
        return [(path, total) for path, total in self.db.execute(stmt).all()]

    def identified_companies(self, since: datetime, limit: int = 20) -> list[SiteVisit]:
        """Última visita de cada sessão que teve empresa identificada, mais recentes primeiro."""
        items, _ = self.list(
            SiteVisit.created_at >= since, SiteVisit.empresa_identificada.is_not(None),
            offset=0, limit=limit, order_by=SiteVisit.created_at.desc(),
        )
        return items
