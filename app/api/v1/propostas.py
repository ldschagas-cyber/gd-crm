"""Rotas de Propostas (RF-PROP)."""
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.common import Page, PageParams
from app.schemas.proposal import PropostaCreate, PropostaRead, PropostaStatusUpdate, PropostaUpdate
from app.services.proposal import PropostaService

router = APIRouter(prefix="/propostas", tags=["Financeiro — Propostas"])


@router.get("", response_model=Page[PropostaRead])
def list_propostas(params: PageParams = Depends(), status: str | None = None, company_id: UUID | None = None,
                   _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    items, total = PropostaService(db).list(params, status, company_id)
    return Page(items=items, total=total, page=params.page, size=params.size)


@router.post("", response_model=PropostaRead, status_code=status.HTTP_201_CREATED)
def create_proposta(data: PropostaCreate, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return PropostaService(db).create(data)


@router.get("/{proposta_id}", response_model=PropostaRead)
def get_proposta(proposta_id: UUID, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return PropostaService(db).get(proposta_id)


@router.put("/{proposta_id}", response_model=PropostaRead)
def update_proposta(proposta_id: UUID, data: PropostaUpdate, _: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    return PropostaService(db).update(proposta_id, data)


@router.post("/{proposta_id}/status", response_model=PropostaRead)
def mudar_status(proposta_id: UUID, data: PropostaStatusUpdate, _: User = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    return PropostaService(db).mudar_status(proposta_id, data.status.value)
