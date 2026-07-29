"""Rotas de modelos de e-mail (§9.5/§9)."""
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.common import Page, PageParams
from app.schemas.email_template import EmailTemplateCreate, EmailTemplateRead, EmailTemplateUpdate
from app.services.email_template import EmailTemplateService

router = APIRouter(prefix="/email-templates", tags=["Modelos de e-mail"])


@router.get("", response_model=Page[EmailTemplateRead])
def list_email_templates(params: PageParams = Depends(), busca: str | None = None,
                          _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    items, total = EmailTemplateService(db).list(params, busca)
    return Page(items=items, total=total, page=params.page, size=params.size)


@router.post("", response_model=EmailTemplateRead, status_code=status.HTTP_201_CREATED)
def create_email_template(data: EmailTemplateCreate, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return EmailTemplateService(db).create(data)


@router.get("/{template_id}", response_model=EmailTemplateRead)
def get_email_template(template_id: UUID, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return EmailTemplateService(db).get(template_id)


@router.put("/{template_id}", response_model=EmailTemplateRead)
def update_email_template(template_id: UUID, data: EmailTemplateUpdate, _: User = Depends(get_current_user),
                          db: Session = Depends(get_db)):
    return EmailTemplateService(db).update(template_id, data)


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_email_template(template_id: UUID, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    EmailTemplateService(db).delete(template_id)
