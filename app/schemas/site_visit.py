"""Schemas de Rastreio do site (item 9.8)."""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class PublicTrackEvent(BaseModel):
    tenant_id: UUID
    session_id: str
    path: str
    referrer: str | None = None


class SiteVisitKpis(BaseModel):
    visitas_30d: int
    visitas_delta_pct: float | None
    empresas_identificadas: int
    taxa_identificacao_pct: float
    negocios_abertos_30d: int


class DailySessions(BaseModel):
    dia: str
    sessoes: int


class TopPage(BaseModel):
    path: str
    visualizacoes: int


class IdentifiedCompanyRow(BaseModel):
    empresa: str
    company_id: UUID | None
    company_status: str | None
    path: str
    origem: str | None
    ultima_visita: datetime
