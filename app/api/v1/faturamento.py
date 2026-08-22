"""Rotas de Faturamento e cobranças (RF-FAT / RF-CAR)."""
from fastapi import APIRouter, Body, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.billing import (
    CobrancaPontualCreate, CobrancaRead, FaturamentoCompetencia, FaturamentoGerar, FaturamentoResult,
)
from app.services.faturamento import FaturamentoService

router = APIRouter(prefix="/faturamento", tags=["Financeiro — Faturamento"])


@router.get("", response_model=FaturamentoCompetencia)
def listar(competencia: str | None = None, _: User = Depends(get_current_user),
           db: Session = Depends(get_db)):
    comp, cobrancas = FaturamentoService(db).listar_competencia(competencia)
    return FaturamentoCompetencia(competencia=comp, cobrancas=cobrancas)


@router.post("/gerar", response_model=FaturamentoResult)
def gerar(data: FaturamentoGerar = Body(default=FaturamentoGerar()),
          _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return FaturamentoService(db).gerar(data.competencia)


@router.post("/reenviar-nf", response_model=FaturamentoResult)
def reenviar_nf(competencia: str = Body(embed=True), _: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    return FaturamentoService(db).reenviar_nf(competencia)


@router.post("/cobrancas", response_model=CobrancaRead, status_code=status.HTTP_201_CREATED)
def criar_pontual(data: CobrancaPontualCreate, _: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    return FaturamentoService(db).criar_pontual(data)
