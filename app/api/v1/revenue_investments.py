"""Rotas de investimento comercial e CAC/ROI — extensão de Previsão Comercial
(ver docs/PLANO_PREVISAO_COMERCIAL.md §8)."""
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_roles
from app.models.user import User, UserRole
from app.schemas.revenue_investment import (
    CacRoiResumo, RevenueInvestmentCreate, RevenueInvestmentRead, RevenueInvestmentUpdate,
)
from app.services.revenue_investment import RevenueInvestmentService

router = APIRouter(prefix="/revenue-investments", tags=["CAC & ROI"])

# Mesmo guard de /dashboards/commercial e do CRUD de metas — investimento é dado sensível,
# só admin/gestor lança ou consulta (vendedor não vê custo).
GESTAO_ROLES = (UserRole.ADMIN.value, UserRole.GESTOR.value)


@router.get("", response_model=list[RevenueInvestmentRead])
def list_investments(
    mes: str | None = Query(default=None, description="Mês no formato AAAA-MM"),
    _: User = Depends(require_roles(*GESTAO_ROLES)),
    db: Session = Depends(get_db),
):
    return RevenueInvestmentService(db).list(mes)


@router.post("", response_model=RevenueInvestmentRead, status_code=status.HTTP_201_CREATED)
def create_investment(
    data: RevenueInvestmentCreate,
    _: User = Depends(require_roles(*GESTAO_ROLES)),
    db: Session = Depends(get_db),
):
    return RevenueInvestmentService(db).create(data)


@router.put("/{investment_id}", response_model=RevenueInvestmentRead)
def update_investment(
    investment_id: UUID,
    data: RevenueInvestmentUpdate,
    _: User = Depends(require_roles(*GESTAO_ROLES)),
    db: Session = Depends(get_db),
):
    return RevenueInvestmentService(db).update(investment_id, data)


@router.delete("/{investment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_investment(
    investment_id: UUID,
    _: User = Depends(require_roles(*GESTAO_ROLES)),
    db: Session = Depends(get_db),
):
    RevenueInvestmentService(db).delete(investment_id)


@router.get("/cac-roi", response_model=CacRoiResumo)
def cac_roi(
    mes: str = Query(..., description="Mês no formato AAAA-MM"),
    _: User = Depends(require_roles(*GESTAO_ROLES)),
    db: Session = Depends(get_db),
):
    return RevenueInvestmentService(db).cac_roi(mes)
