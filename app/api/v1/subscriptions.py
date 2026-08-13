"""Rotas de Assinatura (receita recorrente). Ver docs/PLANO_RECEITA_RECORRENTE.md."""
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.subscription import (
    AssinaturaCancelar, AssinaturaCreate, AssinaturaEventoRead, AssinaturaReativar, AssinaturaRead,
    AssinaturaRenovar, AssinaturaValorUpdate,
)
from app.services.subscription import AssinaturaService

router = APIRouter(prefix="/assinaturas", tags=["Receita Recorrente"])


@router.get("", response_model=list[AssinaturaRead])
def list_assinaturas(
    status_: str | None = None, responsavel_id: UUID | None = None, company_id: UUID | None = None,
    _: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    return AssinaturaService(db).list(status=status_, responsavel_id=responsavel_id, company_id=company_id)


@router.post("", response_model=AssinaturaRead, status_code=status.HTTP_201_CREATED)
def create_assinatura(data: AssinaturaCreate, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return AssinaturaService(db).create(data)


@router.get("/{assinatura_id}", response_model=AssinaturaRead)
def get_assinatura(assinatura_id: UUID, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return AssinaturaService(db).get(assinatura_id)


@router.patch("/{assinatura_id}/valor", response_model=AssinaturaRead)
def atualizar_valor(assinatura_id: UUID, data: AssinaturaValorUpdate,
                    _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return AssinaturaService(db).atualizar_valor(assinatura_id, data)


@router.patch("/{assinatura_id}/cancelar", response_model=AssinaturaRead)
def cancelar_assinatura(assinatura_id: UUID, data: AssinaturaCancelar,
                        _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return AssinaturaService(db).cancelar(assinatura_id, data)


@router.patch("/{assinatura_id}/renovar", response_model=AssinaturaRead)
def renovar_assinatura(assinatura_id: UUID, data: AssinaturaRenovar,
                       _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Customer Success — confirma a renovação do ciclo contratual atual (ver
    docs/PLANO_CUSTOMER_SUCCESS.md). Só se aplica a assinatura com prazo fixo."""
    return AssinaturaService(db).renovar(assinatura_id, data)


@router.patch("/{assinatura_id}/reativar", response_model=AssinaturaRead)
def reativar_assinatura(assinatura_id: UUID, data: AssinaturaReativar,
                        _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return AssinaturaService(db).reativar(assinatura_id, data)


@router.get("/{assinatura_id}/eventos", response_model=list[AssinaturaEventoRead])
def list_eventos(assinatura_id: UUID, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return AssinaturaService(db).list_eventos(assinatura_id)
