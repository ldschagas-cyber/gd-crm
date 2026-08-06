"""Envio real de e-mail para passos de Sequência/Cadência via Microsoft Graph.

Usado pelo Celery Beat (app/workers/tasks.py) para o passo tipo=email: tenta
enviar de verdade pela conta Microsoft 365 do responsável; se não for possível
(sem contato com e-mail, responsável sem integração conectada, Graph fora do
ar), quem chama cai de volta para o comportamento antigo (criar uma Task
manual) — nunca falha silenciosamente o enrollment inteiro.
"""
import re
from datetime import date, datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.contact import Contact
from app.models.deal import Deal
from app.models.email_template import EmailTemplate
from app.models.sequence import Sequence, SequenceEnrollment
from app.models.task import Task
from app.models.timeline import TimelineEvent
from app.models.user import User
from app.repositories.user_integration import UserIntegrationRepository
from app.services.graph_client import GraphClient

VAR_RE = re.compile(r"\{\{(\w+)\}\}")

SEQUENCE_STEP_LABEL = {
    "ligacao": "Ligação", "email": "E-mail", "whatsapp": "WhatsApp",
    "linkedin_conexao": "LinkedIn (conexão)", "linkedin_mensagem": "LinkedIn (mensagem)",
    "tarefa_manual": "Tarefa", "followup": "Follow-up",
}


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


def _resolve_responsavel(db: Session, enrollment: SequenceEnrollment, sequence: Sequence) -> UUID:
    """Responsável da tarefa gerada: dono do negócio > dono da empresa > quem criou a sequência."""
    if enrollment.deal_id:
        deal = db.get(Deal, enrollment.deal_id)
        if deal:
            return deal.responsavel_id
    if enrollment.company_id:
        company = db.get(Company, enrollment.company_id)
        if company and company.responsavel_id:
            return company.responsavel_id
    return sequence.created_by


def _titulo_para_step(db: Session, sequence: Sequence, step) -> str:
    base = SEQUENCE_STEP_LABEL.get(step.tipo, step.tipo)
    if step.template_id:
        template = db.get(EmailTemplate, step.template_id)
        if template:
            return f"{base} — {sequence.nome}: {template.nome}"
    return f"{base} — {sequence.nome}"


def advance_due_steps(db: Session, tenant_id: UUID, enrollment: SequenceEnrollment) -> int:
    """Cria as Tasks (ou envia o e-mail) das etapas já vencidas de um enrollment.

    Chamada tanto pela varredura diária do Celery Beat quanto na hora da
    inscrição (SequenceService.enroll) — assim uma etapa de dia_offset=0 vira
    tarefa imediatamente, em vez de esperar a próxima rodada do cron das 6h
    (RF010, §7.5). Idempotente: só avança enrollment.step_atual a partir de
    quantos dias já se passaram desde iniciado_em, então chamar de novo sem
    tempo adicional decorrido não duplica nada.
    """
    sequence = enrollment.sequence
    steps = sorted(sequence.steps, key=lambda s: s.ordem)
    responsavel_id = _resolve_responsavel(db, enrollment, sequence)
    contact = resolve_contact(db, enrollment.contact_id, enrollment.deal_id)
    hoje = date.today()
    dias_decorridos = (datetime.now(timezone.utc) - enrollment.iniciado_em).days

    criadas = 0
    while enrollment.step_atual < len(steps) and steps[enrollment.step_atual].dia_offset <= dias_decorridos:
        step = steps[enrollment.step_atual]
        enviado = False
        if step.tipo == "email" and step.template_id:
            template = db.get(EmailTemplate, step.template_id)
            company_id = resolve_company_id(db, enrollment.company_id, enrollment.deal_id, contact)
            if template and contact and contact.email and company_id:
                assunto, corpo = render_template(
                    template, contact, db.get(Company, company_id), db.get(User, responsavel_id),
                )
                enviado = send_step_email(db, responsavel_id, contact, assunto, corpo)
                if enviado:
                    log_email_sent(db, tenant_id, company_id, contact.id, enrollment.deal_id, assunto, responsavel_id)
        if not enviado:
            db.add(Task(
                tenant_id=tenant_id, titulo=_titulo_para_step(db, sequence, step), tipo=step.tipo,
                descricao=step.instrucoes,
                responsavel_id=responsavel_id,
                company_id=enrollment.company_id, contact_id=enrollment.contact_id, deal_id=enrollment.deal_id,
                data=hoje,
            ))
        enrollment.step_atual += 1
        criadas += 1

    if enrollment.step_atual >= len(steps):
        enrollment.status = "concluida"
    return criadas
