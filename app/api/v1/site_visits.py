"""Rotas administrativas de Rastreio do site (item 9.8)."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.site_visit import DailySessions, IdentifiedCompanyRow, SiteVisitKpis, TopPage
from app.services.site_visit import SiteVisitService

router = APIRouter(prefix="/site-visits", tags=["Rastreio do site"])


@router.get("/kpis", response_model=SiteVisitKpis)
def get_site_kpis(_: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return SiteVisitService(db).kpis()


@router.get("/daily", response_model=list[DailySessions])
def get_daily_sessions(days: int = Query(14, ge=1, le=90), _: User = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    return SiteVisitService(db).daily_sessions(days)


@router.get("/pages", response_model=list[TopPage])
def get_top_pages(days: int = Query(30, ge=1, le=365), limit: int = Query(10, ge=1, le=50),
                  _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return SiteVisitService(db).top_pages(days, limit)


@router.get("/companies", response_model=list[IdentifiedCompanyRow])
def get_identified_companies(days: int = Query(30, ge=1, le=365), limit: int = Query(20, ge=1, le=100),
                             _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return SiteVisitService(db).identified_companies(days, limit)
