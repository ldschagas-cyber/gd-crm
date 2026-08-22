"""Rotas do Dashboard financeiro (Visão Geral) e categorias (RF-DSH / RF-CAT)."""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.finance_category import CategoriaTipo
from app.models.user import User
from app.schemas.billing import CategoriaCreate, CategoriaRead
from app.schemas.finance_dashboard import FinanceiroResumo
from app.services.finance_category import CategoriaService
from app.services.financeiro_dashboard import FinanceiroDashboardService

router = APIRouter(prefix="/financeiro", tags=["Financeiro — Visão Geral"])


@router.get("/resumo", response_model=FinanceiroResumo)
def resumo(_: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return FinanceiroDashboardService(db).resumo()


@router.get("/categorias", response_model=list[CategoriaRead])
def list_categorias(tipo: str = CategoriaTipo.RECEITA.value, _: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    return CategoriaService(db).list(tipo)


@router.post("/categorias", response_model=CategoriaRead, status_code=status.HTTP_201_CREATED)
def create_categoria(data: CategoriaCreate, _: User = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    return CategoriaService(db).create(data)
