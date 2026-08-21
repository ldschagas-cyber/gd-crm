"""Rotas de Contratos (RF-CONTR). Sem CRUD de tela nesta fase: leitura + ativação."""
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.contract import ContratoAtivar, ContratoRead
from app.services.contract import ContratoService

router = APIRouter(prefix="/contratos", tags=["Financeiro — Contratos"])


@router.get("", response_model=list[ContratoRead])
def list_contratos(status: str | None = None, _: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    return ContratoService(db).list(status)


@router.get("/{contrato_id}", response_model=ContratoRead)
def get_contrato(contrato_id: UUID, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ContratoService(db).get(contrato_id)


@router.post("/{contrato_id}/ativar", response_model=ContratoRead)
def ativar_contrato(contrato_id: UUID, data: ContratoAtivar | None = None,
                    _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ContratoService(db).ativar(contrato_id, data)
