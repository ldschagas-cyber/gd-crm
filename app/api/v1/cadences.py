"""Rotas de Cadências (RF011, §7.6)."""
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.cadence import (
    CadenceCreate, CadenceEnrollmentCreate, CadenceEnrollmentRead, CadenceRead, CadenceUpdate,
)
from app.schemas.common import Page, PageParams
from app.services.cadence import CadenceService

router = APIRouter(prefix="/cadences", tags=["Cadências"])


@router.get("", response_model=Page[CadenceRead])
def list_cadences(params: PageParams = Depends(), busca: str | None = None,
                   _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    items, total = CadenceService(db).list(params, busca)
    return Page(items=items, total=total, page=params.page, size=params.size)


@router.post("", response_model=CadenceRead, status_code=status.HTTP_201_CREATED)
def create_cadence(data: CadenceCreate, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return CadenceService(db).create(data)


@router.get("/{cadence_id}", response_model=CadenceRead)
def get_cadence(cadence_id: UUID, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return CadenceService(db).get(cadence_id)


@router.put("/{cadence_id}", response_model=CadenceRead)
def update_cadence(cadence_id: UUID, data: CadenceUpdate, _: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    return CadenceService(db).update(cadence_id, data)


@router.delete("/{cadence_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_cadence(cadence_id: UUID, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    CadenceService(db).delete(cadence_id)


@router.post("/{cadence_id}/clone", response_model=CadenceRead, status_code=status.HTTP_201_CREATED)
def clone_cadence(cadence_id: UUID, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return CadenceService(db).clone(cadence_id)


@router.get("/{cadence_id}/enrollments", response_model=list[CadenceEnrollmentRead])
def list_enrollments(cadence_id: UUID, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return CadenceService(db).list_enrollments(cadence_id)


@router.post("/{cadence_id}/enrollments", response_model=CadenceEnrollmentRead, status_code=status.HTTP_201_CREATED)
def create_enrollment(cadence_id: UUID, data: CadenceEnrollmentCreate, _: User = Depends(get_current_user),
                      db: Session = Depends(get_db)):
    return CadenceService(db).enroll(cadence_id, data)
