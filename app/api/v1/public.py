"""Rotas públicas (sem autenticação): widget de formulário embutido no site,
beacon de rastreio de páginas (item 9.8) e webhooks de voz do Twilio. O
tenant é resolvido pelo próprio form_id (formulários), pelo tenant_id
embutido no snippet (rastreio), pela identidade do usuário no Access Token
do Voice SDK (chamada de saída) ou por TWILIO_TENANT_ID (chamada de entrada)
— nunca por JWT, já que quem chama essas rotas nunca é um usuário logado no
CRM (visitante do site ou o próprio Twilio)."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.context import set_current_tenant, set_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.form import FormSubmissionRead, PublicFormSubmit
from app.schemas.site_visit import PublicTrackEvent
from app.services.form import FormService
from app.services.site_visit import SiteVisitService
from app.services.twilio_voice import (
    active_client_identities, build_inbound_twiml, build_outbound_twiml,
    is_configured, record_call_started, record_call_status, resolve_caller, validate_signature,
)

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


async def _twilio_form(request: Request) -> dict:
    """Valida a assinatura antes de confiar em qualquer campo do POST.

    A URL usada na validação precisa ser exatamente a que o Twilio chamou
    (`TWILIO_VOICE_WEBHOOK_BASE_URL` + path/query) — `request.url` reflete o
    que o Starlette enxerga atrás do proxy reverso (nginx-proxy.conf), que
    pode não bater em scheme/host/porta com o que o Twilio usou pra assinar.
    """
    if not is_configured():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Chamadas não configuradas.")
    form = dict(await request.form())
    signature = request.headers.get("X-Twilio-Signature", "")
    base = (settings.TWILIO_VOICE_WEBHOOK_BASE_URL or "").rstrip("/")
    url = f"{base}{request.url.path}"
    if request.url.query:
        url = f"{url}?{request.url.query}"
    if not validate_signature(url, form, signature):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Assinatura Twilio inválida.")
    return form


def _status_callback_url() -> str:
    base = (settings.TWILIO_VOICE_WEBHOOK_BASE_URL or "").rstrip("/")
    return f"{base}{settings.API_V1_PREFIX}/public/twilio/status"


@router.post("/twilio/voice", include_in_schema=False)
async def twilio_voice(request: Request, db: Session = Depends(get_db)):
    """Voice Request URL do TwiML App — chamada de SAÍDA disparada pelo
    `Device.connect()` do navegador (Voice SDK). `From` chega como
    `client:<user_id>` (identity do Access Token, atribuída pelo próprio
    Twilio — não é um valor que o chamador possa forjar)."""
    form = await _twilio_form(request)
    to_number = form.get("To", "")
    identity = (form.get("From") or "").removeprefix("client:")
    try:
        user = db.get(User, UUID(identity))
    except ValueError:
        user = None
    if user is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Usuário do Access Token não encontrado.")

    set_current_tenant(user.tenant_id)
    set_current_user(user.id)

    def _uuid_or_none(value: str | None) -> UUID | None:
        try:
            return UUID(value) if value else None
        except ValueError:
            return None

    record_call_started(
        db, tenant_id=user.tenant_id, call_sid=form.get("CallSid", ""), direcao="outbound",
        de_numero=settings.TWILIO_PHONE_NUMBER, para_numero=to_number, user_id=user.id,
        contact_id=_uuid_or_none(form.get("ContactId")), company_id=_uuid_or_none(form.get("CompanyId")),
        deal_id=_uuid_or_none(form.get("DealId")),
    )
    twiml = build_outbound_twiml(to_number, _status_callback_url())
    return Response(content=twiml, media_type="application/xml")


@router.post("/twilio/inbound-voice", include_in_schema=False)
async def twilio_inbound_voice(request: Request, db: Session = Depends(get_db)):
    """'A call comes in' do número Twilio — chamada de ENTRADA, sem
    identidade de usuário disponível (ligação fria). Toca em paralelo em
    todos os usuários ativos do tenant dono do número (TWILIO_TENANT_ID —
    simplificação do MVP, ver app/services/twilio_voice.py)."""
    form = await _twilio_form(request)
    if not settings.TWILIO_TENANT_ID:
        return Response(content=build_inbound_twiml([], _status_callback_url()), media_type="application/xml")

    tenant_id = UUID(settings.TWILIO_TENANT_ID)
    set_current_tenant(tenant_id)

    from_number = form.get("From", "")
    caller = resolve_caller(db, tenant_id, from_number)
    record_call_started(
        db, tenant_id=tenant_id, call_sid=form.get("CallSid", ""), direcao="inbound",
        de_numero=from_number, para_numero=form.get("To"),
        contact_id=caller["contact_id"], company_id=caller["company_id"],
    )
    identities = active_client_identities(db, tenant_id)
    twiml = build_inbound_twiml(identities, _status_callback_url())
    return Response(content=twiml, media_type="application/xml")


@router.post("/twilio/status", include_in_schema=False)
async def twilio_status_callback(request: Request, db: Session = Depends(get_db)):
    """statusCallback de ambas as direções — só atualiza a Call já criada em
    /twilio/voice ou /twilio/inbound-voice (busca sem tenant no contexto
    ainda, resolvido a partir da própria Call por `call_sid`)."""
    form = await _twilio_form(request)
    duration = form.get("CallDuration")
    record_call_status(
        db, call_sid=form.get("CallSid", ""), status=form.get("CallStatus", ""),
        duracao_segundos=int(duration) if duration and duration.isdigit() else None,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
