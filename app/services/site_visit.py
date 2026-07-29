"""Serviço de Rastreio do site: recepção de pageviews públicos + KPIs/consultas
administrativas (item 9.8)."""
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.context import get_current_tenant, set_current_tenant
from app.models.company import Company
from app.models.deal import Deal
from app.models.site_visit import SiteVisit
from app.repositories.company import CompanyRepository
from app.repositories.site_visit import SiteVisitRepository
from app.schemas.site_visit import (
    DailySessions, IdentifiedCompanyRow, PublicTrackEvent, SiteVisitKpis, TopPage,
)
from app.services.ip_lookup import lookup_company_by_ip


def _classify_origem(referrer: str | None) -> str:
    if not referrer:
        return "Direto"
    host = urlparse(referrer).hostname or ""
    if "google." in host:
        return "Google orgânico"
    if "linkedin." in host:
        return "LinkedIn"
    if "bing." in host:
        return "Bing orgânico"
    return "Outro site"


class SiteVisitService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = SiteVisitRepository(db)

    # ---- recepção pública (sem auth) -----------------------------------------
    def track(self, data: PublicTrackEvent, ip: str | None) -> None:
        set_current_tenant(data.tenant_id)
        empresa_nome = lookup_company_by_ip(ip)
        company_id = None
        if empresa_nome:
            company = CompanyRepository(self.db).get_by_name(empresa_nome)
            if company is not None:
                company_id = company.id
        self.repo.add(SiteVisit(
            session_id=data.session_id, path=data.path, referrer=data.referrer,
            origem=_classify_origem(data.referrer), ip=ip,
            empresa_identificada=empresa_nome, company_id=company_id,
        ))

    # ---- consultas administrativas -------------------------------------------
    def kpis(self) -> SiteVisitKpis:
        now = datetime.now(timezone.utc)
        since = now - timedelta(days=30)
        since_anterior = now - timedelta(days=60)

        visitas_30d = self._count_since(since)
        visitas_periodo_anterior = self._count_since(since_anterior, until=since)
        delta = None
        if visitas_periodo_anterior > 0:
            delta = round((visitas_30d - visitas_periodo_anterior) / visitas_periodo_anterior * 100, 1)

        sessoes_total = self._distinct_sessions_since(since)
        sessoes_identificadas = self._distinct_sessions_since(since, only_identified=True)
        taxa = round(sessoes_identificadas / sessoes_total * 100, 1) if sessoes_total > 0 else 0.0

        empresas_identificadas = self.db.execute(
            select(func.count(func.distinct(SiteVisit.empresa_identificada)))
            .where(SiteVisit.tenant_id == get_current_tenant(), SiteVisit.created_at >= since,
                  SiteVisit.empresa_identificada.is_not(None))
        ).scalar_one()

        company_ids = [
            row[0] for row in self.db.execute(
                select(func.distinct(SiteVisit.company_id))
                .where(SiteVisit.tenant_id == get_current_tenant(), SiteVisit.created_at >= since,
                      SiteVisit.company_id.is_not(None))
            ).all()
        ]
        negocios_abertos = 0
        if company_ids:
            negocios_abertos = self.db.execute(
                select(func.count()).select_from(Deal).where(
                    Deal.tenant_id == get_current_tenant(), Deal.company_id.in_(company_ids),
                    Deal.created_at >= since,
                )
            ).scalar_one()

        return SiteVisitKpis(
            visitas_30d=visitas_30d, visitas_delta_pct=delta,
            empresas_identificadas=empresas_identificadas, taxa_identificacao_pct=taxa,
            negocios_abertos_30d=negocios_abertos,
        )

    def _count_since(self, since: datetime, until: datetime | None = None) -> int:
        filtros = [SiteVisit.tenant_id == get_current_tenant(), SiteVisit.created_at >= since]
        if until:
            filtros.append(SiteVisit.created_at < until)
        return self.db.execute(select(func.count()).select_from(SiteVisit).where(*filtros)).scalar_one()

    def _distinct_sessions_since(self, since: datetime, only_identified: bool = False) -> int:
        filtros = [SiteVisit.tenant_id == get_current_tenant(), SiteVisit.created_at >= since]
        if only_identified:
            filtros.append(SiteVisit.empresa_identificada.is_not(None))
        return self.db.execute(
            select(func.count(func.distinct(SiteVisit.session_id))).where(*filtros)
        ).scalar_one()

    def daily_sessions(self, days: int = 14) -> list[DailySessions]:
        since = datetime.now(timezone.utc) - timedelta(days=days)
        return [DailySessions(dia=dia, sessoes=total) for dia, total in self.repo.sessions_per_day(since)]

    def top_pages(self, days: int = 30, limit: int = 10) -> list[TopPage]:
        since = datetime.now(timezone.utc) - timedelta(days=days)
        return [TopPage(path=path, visualizacoes=total) for path, total in self.repo.top_pages(since, limit)]

    def identified_companies(self, days: int = 30, limit: int = 20) -> list[IdentifiedCompanyRow]:
        since = datetime.now(timezone.utc) - timedelta(days=days)
        visits = self.repo.identified_companies(since, limit)
        company_ids = [v.company_id for v in visits if v.company_id]
        statuses = {}
        if company_ids:
            for c in self.db.execute(select(Company).where(Company.id.in_(company_ids))).scalars():
                statuses[c.id] = c.status
        return [
            IdentifiedCompanyRow(
                empresa=v.empresa_identificada, company_id=v.company_id,
                company_status=statuses.get(v.company_id), path=v.path, origem=v.origem,
                ultima_visita=v.created_at,
            )
            for v in visits
        ]
