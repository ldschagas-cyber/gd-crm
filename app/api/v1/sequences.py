"""Rotas de Sequências (RF010, §7.5)."""
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.common import Page, PageParams
from app.schemas.sequence import (
    SequenceCreate, SequenceEnrollmentCreate, SequenceEnrollmentRead, SequenceRead, SequenceUpdate,
)
from app.services.sequence import SequenceService

router = APIRouter(prefix="/sequences", tags=["Sequências"])


@router.get("", response_model=Page[SequenceRead])
def list_sequences(params: PageParams = Depends(), busca: str | None = None,
                    _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    items, total = SequenceService(db).list(params, busca)
    return Page(items=items, total=total, page=params.page, size=params.size)


@router.post("", response_model=SequenceRead, status_code=status.HTTP_201_CREATED)
def create_sequence(data: SequenceCreate, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return SequenceService(db).create(data)


@router.get("/{sequence_id}", response_model=SequenceRead)
def get_sequence(sequence_id: UUID, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return SequenceService(db).get(sequence_id)


@router.put("/{sequence_id}", response_model=SequenceRead)
def update_sequence(sequence_id: UUID, data: SequenceUpdate, _: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    return SequenceService(db).update(sequence_id, data)


@router.delete("/{sequence_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_sequence(sequence_id: UUID, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    SequenceService(db).delete(sequence_id)


@router.post("/{sequence_id}/clone", response_model=SequenceRead, status_code=status.HTTP_201_CREATED)
def clone_sequence(sequence_id: UUID, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return SequenceService(db).clone(sequence_id)


@router.get("/{sequence_id}/enrollments", response_model=list[SequenceEnrollmentRead])
def list_enrollments(sequence_id: UUID, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return SequenceService(db).list_enrollments(sequence_id)


@router.post("/{sequence_id}/enrollments", response_model=SequenceEnrollmentRead, status_code=status.HTTP_201_CREATED)
def create_enrollment(sequence_id: UUID, data: SequenceEnrollmentCreate, _: User = Depends(get_current_user),
                      db: Session = Depends(get_db)):
    return SequenceService(db).enroll(sequence_id, data)
