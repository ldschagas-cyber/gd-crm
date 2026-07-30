"""Rotas de referência CNAE (§ Buscar Empresas) — dado global, sem escopo de tenant."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.cnae_code import CnaeCodeRead
from app.services.cnae_code import CnaeCodeService

router = APIRouter(prefix="/cnae-codes", tags=["CNAE"])


@router.get("/search", response_model=list[CnaeCodeRead])
def search_cnae(
    busca: str = Query(min_length=2),
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return CnaeCodeService(db).search(busca)


@router.get("/{codigo}/similares", response_model=list[CnaeCodeRead])
def similares_cnae(
    codigo: str,
    nivel: str = Query("classe", pattern="^(subclasse|classe|grupo|divisao)$"),
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return CnaeCodeService(db).similares(codigo, nivel)
