"""Rotas públicas (sem autenticação): widget de formulário embutido no site e
beacon de rastreio de páginas (item 9.8). O tenant é resolvido pelo próprio
form_id (formulários) ou pelo tenant_id embutido no snippet (rastreio) — nunca
por JWT, já que quem chama é o navegador do visitante do site, não um usuário
logado no CRM."""
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.form import FormSubmissionRead, PublicFormSubmit
from app.schemas.site_visit import PublicTrackEvent
from app.services.form import FormService
from app.services.site_visit import SiteVisitService

router = APIRouter(prefix="/public", tags=["Público (sem autenticação)"])


def _client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


@router.post("/forms/{form_id}/submit", response_model=FormSubmissionRead, status_code=status.HTTP_201_CREATED)
def submit_form(form_id: UUID, data: PublicFormSubmit, request: Request, db: Session = Depends(get_db)):
    return FormService(db).submit_public(form_id, data, _client_ip(request))


@router.post("/track", status_code=status.HTTP_204_NO_CONTENT)
def track_page_view(data: PublicTrackEvent, request: Request, db: Session = Depends(get_db)):
    SiteVisitService(db).track(data, _client_ip(request))
    return None
