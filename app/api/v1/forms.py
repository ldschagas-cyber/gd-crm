"""Rotas administrativas de Formulários (item 9.8)."""
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.common import Page, PageParams
from app.schemas.form import FormCreate, FormKpis, FormRead, FormSubmissionRead, FormUpdate
from app.services.form import FormService

router = APIRouter(prefix="/forms", tags=["Formulários"])


@router.get("", response_model=list[FormRead])
def list_forms(_: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return FormService(db).list()


@router.post("", response_model=FormRead, status_code=status.HTTP_201_CREATED)
def create_form(data: FormCreate, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return FormService(db).create(data)


@router.get("/kpis", response_model=FormKpis)
def get_forms_kpis(_: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return FormService(db).kpis()


@router.get("/{form_id}", response_model=FormRead)
def get_form(form_id: UUID, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return FormService(db).get(form_id)


@router.put("/{form_id}", response_model=FormRead)
def update_form(form_id: UUID, data: FormUpdate, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return FormService(db).update(form_id, data)


@router.get("/{form_id}/submissions", response_model=Page[FormSubmissionRead])
def list_form_submissions(form_id: UUID, params: PageParams = Depends(),
                          _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    items, total = FormService(db).list_submissions(form_id, params)
    return Page(items=items, total=total, page=params.page, size=params.size)
