"""Rotas de Metas de Venda — quantidade e valor por vendedor e equipe, por mês.
Restritas a admin e gestor (mesmo critério das Metas do Funil)."""
from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_roles
from app.models.user import User, UserRole
from app.schemas.metas_venda import MetasVendaResumo, SalesTargetInput
from app.services.metas_venda import MetasVendaService

router = APIRouter(prefix="/metas-venda", tags=["Metas de Venda"])
gestor = require_roles(UserRole.ADMIN.value, UserRole.GESTOR.value)


@router.get("/resumo", response_model=MetasVendaResumo)
def get_resumo(
    mes: str = Query(..., pattern=r"^\d{4}-\d{2}$"),
    _: User = Depends(gestor),
    db: Session = Depends(get_db),
):
    return MetasVendaService(db).resumo(mes)


@router.put("/targets", response_model=MetasVendaResumo)
def set_targets(
    mes: str = Query(..., pattern=r"^\d{4}-\d{2}$"),
    items: list[SalesTargetInput] = Body(...),
    _: User = Depends(gestor),
    db: Session = Depends(get_db),
):
    return MetasVendaService(db).set_targets(mes, items)
