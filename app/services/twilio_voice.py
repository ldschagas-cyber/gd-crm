"""Chamadas de voz via Twilio (Preferências → Chamadas).

Duas rotas públicas (`app/api/v1/public.py`) chamam este serviço sem contexto
de tenant pronto — `voice` (saída, disparada pelo `Device.connect()` do
navegador) resolve o tenant a partir do usuário logado no Voice SDK (`From`);
`inbound_voice` (entrada, "A call comes in" da configuração do número) não
tem identidade nenhuma pra partir, então usa `TWILIO_TENANT_ID` — simplificação
do MVP: só existe 1 número Twilio configurado hoje, sem tabela de roteamento
número→tenant.
"""
import re
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session
from twilio.jwt.access_token import AccessToken
from twilio.jwt.access_token.grants import VoiceGrant
from twilio.request_validator import RequestValidator
from twilio.twiml.voice_response import Client, Dial, Number, Say, VoiceResponse

from app.core.config import settings
from app.core.context import get_current_user_id, set_current_tenant, set_current_user
from app.models.call import Call
from app.models.company import Company
from app.models.contact import Contact
from app.models.user import User, UserStatus
from app.repositories.call import CallRepository
from app.services.timeline import TimelineService


def is_configured() -> bool:
    return bool(
        settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN
        and settings.TWILIO_API_KEY_SID and settings.TWILIO_API_KEY_SECRET
        and settings.TWILIO_TWIML_APP_SID and settings.TWILIO_PHONE_NUMBER
    )


def mint_access_token(user: User) -> str:
    token = AccessToken(
        settings.TWILIO_ACCOUNT_SID, settings.TWILIO_API_KEY_SID, settings.TWILIO_API_KEY_SECRET,
        identity=str(user.id), ttl=3600,
    )
    token.add_grant(VoiceGrant(
        outgoing_application_sid=settings.TWILIO_TWIML_APP_SID,
        incoming_allow=True,
    ))
    return token.to_jwt()


def validate_signature(url: str, params: dict, signature: str) -> bool:
    """`url` precisa ser a URL pública exata que o Twilio chamou
    (`TWILIO_VOICE_WEBHOOK_BASE_URL` + path), não `request.url` do FastAPI —
    atrás do proxy reverso (nginx-proxy.conf) o scheme/host que o Starlette
    enxerga pode não bater com o que o Twilio usou pra assinar."""
    return RequestValidator(settings.TWILIO_AUTH_TOKEN).validate(url, params, signature)


def _digits(numero: str | None) -> str:
    return re.sub(r"\D", "", numero or "")


def _phone_matches(a: str | None, b: str | None) -> bool:
    da, db_ = _digits(a), _digits(b)
    if len(da) < 8 or len(db_) < 8:
        return False
    return da.endswith(db_[-8:]) or db_.endswith(da[-8:])


def resolve_caller(db: Session, tenant_id: UUID, numero: str) -> dict:
    """Casa `numero` (quem está ligando) com Contato/Empresa cadastrados,
    pelos últimos 8 dígitos (tolera diferença de DDI/DDD registrado)."""
    contacts = db.execute(select(Contact).where(Contact.tenant_id == tenant_id)).scalars().all()
    for contact in contacts:
        if _phone_matches(contact.telefone, numero) or _phone_matches(contact.whatsapp, numero):
            company = db.get(Company, contact.company_id)
            return {
                "label": f"{contact.nome} — {company.razao_social}" if company else contact.nome,
                "contact_id": contact.id,
                "company_id": contact.company_id,
            }
    companies = db.execute(select(Company).where(Company.tenant_id == tenant_id)).scalars().all()
    for company in companies:
        if _phone_matches(company.telefone, numero):
            return {"label": company.razao_social, "contact_id": None, "company_id": company.id}
    return {"label": None, "contact_id": None, "company_id": None}


def build_outbound_twiml(to_number: str, status_callback_url: str) -> str:
    response = VoiceResponse()
    dial = Dial(caller_id=settings.TWILIO_PHONE_NUMBER)
    dial.append(Number(
        to_number, status_callback=status_callback_url,
        status_callback_event="completed", status_callback_method="POST",
    ))
    response.append(dial)
    return str(response)


def build_inbound_twiml(identities: list[str], status_callback_url: str) -> str:
    response = VoiceResponse()
    if not identities:
        response.append(Say(language="pt-BR", text="No momento não há ninguém disponível para atender. Tente novamente mais tarde."))
        return str(response)
    dial = Dial(
        timeout=20, status_callback=status_callback_url,
        status_callback_event="completed", status_callback_method="POST",
    )
    for identity in identities:
        dial.append(Client(identity))
    response.append(dial)
    response.append(Say(language="pt-BR", text="Não foi possível atender sua ligação agora. Tente novamente mais tarde."))
    return str(response)


def active_client_identities(db: Session, tenant_id: UUID) -> list[str]:
    users = db.execute(
        select(User).where(User.tenant_id == tenant_id, User.status == UserStatus.ATIVO.value)
    ).scalars().all()
    return [str(u.id) for u in users]


def record_call_started(
    db: Session, tenant_id: UUID, call_sid: str, direcao: str,
    de_numero: str | None, para_numero: str | None,
    user_id: UUID | None = None, contact_id: UUID | None = None, company_id: UUID | None = None,
    deal_id: UUID | None = None,
) -> Call:
    calls = CallRepository(db)
    existing = calls.get_by_sid_any_tenant(call_sid)
    if existing:
        return existing
    call = Call(
        tenant_id=tenant_id, call_sid=call_sid, direcao=direcao,
        de_numero=de_numero, para_numero=para_numero, status="iniciada",
        user_id=user_id or get_current_user_id(), contact_id=contact_id, company_id=company_id,
        deal_id=deal_id,
    )
    db.add(call)
    db.flush()
    return call


def record_call_status(db: Session, call_sid: str, status: str, duracao_segundos: int | None) -> Call | None:
    call = CallRepository(db).get_by_sid_any_tenant(call_sid)
    if call is None:
        return None
    call.status = status
    call.duracao_segundos = duracao_segundos
    db.flush()

    if call.company_id is not None:
        set_current_tenant(call.tenant_id)
        set_current_user(call.user_id)
        titulo = "Ligação recebida" if call.direcao == "inbound" else "Ligação realizada"
        descricao = f"Duração: {duracao_segundos or 0}s — status: {status}"
        TimelineService(db).registrar(
            call.company_id, "ligacao", titulo, descricao,
            deal_id=call.deal_id, contact_id=call.contact_id,
            meta={"call_sid": call_sid, "direcao": call.direcao, "duracao_segundos": duracao_segundos, "status": status},
        )
    return call
