"""Rotas de indicadores de Receita Recorrente — MRR/ARR/Churn/Expansão/NRR/LTV.
Dado agregado de carteira, dado sensível: mesmo guard de /dashboards/commercial e
/revenue-investments (só admin/gestor). Ver docs/PLANO_RECEITA_RECORRENTE.md."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_roles
from app.models.user import User, UserRole
from app.schemas.subscription import RevenuePeriodo, RevenueResumo, RevenueWaterfall
from app.services.revenue import RevenueService

router = APIRouter(prefix="/receita-recorrente", tags=["Receita Recorrente"])

GESTAO_ROLES = (UserRole.ADMIN.value, UserRole.GESTOR.value)


@router.get("/resumo", response_model=RevenueResumo)
def resumo(
    periodo: RevenuePeriodo = Query(RevenuePeriodo.MES),
    _: User = Depends(require_roles(*GESTAO_ROLES)),
    db: Session = Depends(get_db),
):
    return RevenueService(db).resumo(periodo)


@router.get("/waterfall", response_model=RevenueWaterfall)
def waterfall(
    meses: int = Query(6, ge=1, le=24),
    _: User = Depends(require_roles(*GESTAO_ROLES)),
    db: Session = Depends(get_db),
):
    return RevenueService(db).waterfall(meses)
