"""Envio real de e-mail para passos de Sequência/Cadência via Microsoft Graph.

Usado pelo Celery Beat (app/workers/tasks.py) para o passo tipo=email: tenta
enviar de verdade pela conta Microsoft 365 do responsável; se não for possível
(sem contato com e-mail, responsável sem integração conectada, Graph fora do
ar), quem chama cai de volta para o comportamento antigo (criar uma Task
manual) — nunca falha silenciosamente o enrollment inteiro.
"""
import re
from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.contact import Contact
from app.models.deal import Deal
from app.models.email_template import EmailTemplate
from app.models.timeline import TimelineEvent
from app.models.user import User
from app.repositories.user_integration import UserIntegrationRepository
from app.services.graph_client import GraphClient

VAR_RE = re.compile(r"\{\{(\w+)\}\}")


def resolve_contact(db: Session, contact_id: UUID | None, deal_id: UUID | None) -> Contact | None:
    """Contato de destino do enrollment: direto, ou via contato principal do negócio."""
    if contact_id:
        return db.get(Contact, contact_id)
    if deal_id:
        deal = db.get(Deal, deal_id)
        if deal and deal.contact_id:
            return db.get(Contact, deal.contact_id)
    return None


def resolve_company_id(db: Session, company_id: UUID | None, deal_id: UUID | None,
                        contact: Contact | None = None) -> UUID | None:
    if company_id:
        return company_id
    if deal_id:
        deal = db.get(Deal, deal_id)
        if deal:
            return deal.company_id
    if contact:
        return contact.company_id
    return None


def render_template(template: EmailTemplate, contact: Contact, company: Company | None, responsavel: User | None) -> tuple[str, str]:
    valores = {
        "nome": contact.nome,
        "empresa": (company.nome_fantasia or company.razao_social) if company else "",
        "cargo": contact.cargo or "",
        "responsavel": responsavel.nome if responsavel else "",
        "contexto_pessoal": contact.contexto_pessoal or "",
        "contexto_rapido": (company.contexto_rapido or "") if company else "",
    }

    def _sub(texto: str) -> str:
        return VAR_RE.sub(lambda m: valores.get(m.group(1), m.group(0)), texto)

    return _sub(template.assunto), _sub(template.corpo)


def has_active_email_integration(db: Session, user_id: UUID) -> bool:
    row = UserIntegrationRepository(db).get_by_user_tipo(user_id, "email")
    return bool(row and row.ativo)


def has_replied(db: Session, responsavel_id: UUID, contact_email: str, since: datetime) -> bool:
    """Varre a caixa de entrada do responsável por uma mensagem do contato após `since`.

    Falha aberta (retorna False) para qualquer erro de Graph — um problema de
    rede/token não pode travar a sequência inteira, só significa "não detectou
    resposta ainda", igual ao comportamento de antes de existir essa checagem.
    """
    try:
        mensagens = GraphClient(db).search_mail(responsavel_id, contact_email, top=10)
    except Exception:
        return False
    for msg in mensagens:
        remetente = ((msg.get("from") or {}).get("emailAddress") or {}).get("address", "")
        if remetente.lower() != contact_email.lower():
            continue
        recebido = msg.get("receivedDateTime")
        if not recebido:
            continue
        recebido_dt = datetime.fromisoformat(recebido.replace("Z", "+00:00"))
        if recebido_dt > since:
            return True
    return False


def send_step_email(db: Session, responsavel_id: UUID, contact: Contact | None, subject: str, body: str) -> bool:
    if not contact or not contact.email:
        return False
    try:
        GraphClient(db).send_mail(responsavel_id, contact.email, subject, body)
    except Exception:
        return False
    return True


def log_email_sent(db: Session, tenant_id: UUID, company_id: UUID, contact_id: UUID | None,
                    deal_id: UUID | None, subject: str, user_id: UUID) -> None:
    db.add(TimelineEvent(
        tenant_id=tenant_id, company_id=company_id, contact_id=contact_id, deal_id=deal_id,
        tipo="email", titulo=subject, user_id=user_id,
        evento_meta={"enviado_automatico": True},
    ))
