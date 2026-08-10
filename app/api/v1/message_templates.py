"""Rotas de modelos de mensagem (WhatsApp/LinkedIn)."""
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.common import Page, PageParams
from app.schemas.message_template import MessageTemplateCreate, MessageTemplateRead, MessageTemplateUpdate
from app.services.message_template import MessageTemplateService

router = APIRouter(prefix="/message-templates", tags=["Modelos de mensagem"])


@router.get("", response_model=Page[MessageTemplateRead])
def list_message_templates(params: PageParams = Depends(), busca: str | None = None, canal: str | None = None,
                            _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    items, total = MessageTemplateService(db).list(params, busca, canal)
    return Page(items=items, total=total, page=params.page, size=params.size)


@router.post("", response_model=MessageTemplateRead, status_code=status.HTTP_201_CREATED)
def create_message_template(data: MessageTemplateCreate, _: User = Depends(get_current_user),
                             db: Session = Depends(get_db)):
    return MessageTemplateService(db).create(data)


@router.get("/{template_id}", response_model=MessageTemplateRead)
def get_message_template(template_id: UUID, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return MessageTemplateService(db).get(template_id)


@router.put("/{template_id}", response_model=MessageTemplateRead)
def update_message_template(template_id: UUID, data: MessageTemplateUpdate, _: User = Depends(get_current_user),
                             db: Session = Depends(get_db)):
    return MessageTemplateService(db).update(template_id, data)


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_message_template(template_id: UUID, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    MessageTemplateService(db).delete(template_id)
