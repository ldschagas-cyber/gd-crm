"""Rotas de Metas de Ligações — meta por mês (semanal/mensal) por vendedor.
Restritas a admin e gestor (mesmo critério das Metas de Venda)."""
from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_roles
from app.models.user import User, UserRole
from app.schemas.metas_ligacoes import CallTargetInput, MetaLigacoesResponse
from app.services.metas_ligacoes import MetasLigacoesService

router = APIRouter(prefix="/metas-ligacoes", tags=["Metas de Ligações"])
gestor = require_roles(UserRole.ADMIN.value, UserRole.GESTOR.value)


@router.get("/progresso", response_model=MetaLigacoesResponse)
def get_progresso(
    mes: str = Query(..., pattern=r"^\d{4}-\d{2}$"),
    _: User = Depends(gestor),
    db: Session = Depends(get_db),
):
    return MetasLigacoesService(db).progresso(mes)


@router.put("/targets", response_model=MetaLigacoesResponse)
def set_targets(
    mes: str = Query(..., pattern=r"^\d{4}-\d{2}$"),
    items: list[CallTargetInput] = Body(...),
    _: User = Depends(gestor),
    db: Session = Depends(get_db),
):
    return MetasLigacoesService(db).set_targets(mes, items)
