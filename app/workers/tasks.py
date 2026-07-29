"""Tarefas Celery: importação assíncrona de empresas e contatos (Excel/CSV) e automações."""
import base64
import io
from datetime import date, datetime, timedelta, timezone
from uuid import UUID

import pandas as pd
from sqlalchemy import select

from app.core.celery_app import celery_app
from app.core.context import set_current_tenant, set_current_user
from app.core.database import SessionLocal
from app.models.cadence import Cadence, CadenceEnrollment
from app.models.company import Company
from app.models.contact import Contact
from app.models.deal import Deal
from app.models.email_template import EmailTemplate
from app.models.import_job import ImportJob, ImportStatus
from app.models.lead_prospect import LeadProspect, LeadStatus
from app.models.pipeline import PipelineStage
from app.models.sequence import Sequence, SequenceEnrollment
from app.models.task import Task
from app.models.tenant import Tenant
from app.models.user import User
from app.models.workflow import Workflow, WorkflowExecutionLog
from app.repositories.company import CompanyRepository
from app.repositories.contact import ContactRepository
from app.repositories.lead_prospect import LeadProspectRepository
from app.repositories.user import UserRepository
from app.services.sequence_dispatch import (
    has_active_email_integration, has_replied, log_email_sent, render_template,
    resolve_company_id, resolve_contact, send_step_email,
)

COMPANY_REQUIRED = ["razao_social", "cnpj", "cidade", "uf"]
CONTACT_REQUIRED = ["nome", "empresa", "email"]
LEAD_PROSPECT_REQUIRED = ["empresa"]


def _read_table(content: bytes, filename: str) -> pd.DataFrame:
    # dtype=str evita que o pandas infira colunas como cnpj/telefone como numéricas
    # (o que rebatizaria "11222333000144" para "11222333000144.0" e estouraria
    # o VARCHAR(14) do banco) e preserva zeros à esquerda.
    if filename.lower().endswith(".csv"):
        return pd.read_csv(io.BytesIO(content), dtype=str)
    return pd.read_excel(io.BytesIO(content), dtype=str)


@celery_app.task(name="app.workers.tasks.import_companies_task")
def import_companies_task(job_id: str, tenant_id: str, user_id: str, content: str, filename: str):
    """`content` chega em base64 (o broker Celery serializa em JSON, que não aceita bytes crus)."""
    set_current_tenant(UUID(tenant_id))
    set_current_user(UUID(user_id))
    db = SessionLocal()
    try:
        job = db.get(ImportJob, UUID(job_id))
        job.status = ImportStatus.PROCESSANDO.value
        db.flush()
        df = _read_table(base64.b64decode(content), filename)
        repo = CompanyRepository(db)
        erros, importadas = [], 0
        for idx, row in df.iterrows():
            faltando = [c for c in COMPANY_REQUIRED if c not in df.columns or pd.isna(row.get(c))]
            if faltando:
                erros.append({"linha": int(idx) + 2, "motivo": f"Campos obrigatórios ausentes: {faltando}"})
                continue
            cnpj = str(row["cnpj"]).strip()
            if repo.get_by_cnpj(cnpj):
                erros.append({"linha": int(idx) + 2, "motivo": "CNPJ já cadastrado"})
                continue

            def opt_str(col):
                return str(row[col]).strip() if col in df.columns and not pd.isna(row.get(col)) else None

            def opt_int(col):
                val = opt_str(col)
                try:
                    return int(float(val)) if val else None
                except ValueError:
                    return None

            def opt_float(col):
                val = opt_str(col)
                try:
                    return float(val) if val else None
                except ValueError:
                    return None

            repo.add(Company(
                razao_social=str(row["razao_social"]).strip(), cnpj=cnpj,
                cidade=str(row["cidade"]).strip(), uf=str(row["uf"]).strip()[:2],
                segmento=opt_str("segmento"), telefone=opt_str("telefone"), email=opt_str("email"),
                porte=opt_str("porte"), num_funcionarios=opt_int("funcionarios"),
                faturamento_estimado=opt_float("faturamento"), origem=opt_str("origem"),
                created_by=UUID(user_id),
            ))
            importadas += 1
        job.total_linhas = int(len(df))
        job.importadas = importadas
        job.erros = erros
        job.status = ImportStatus.CONCLUIDO.value
        db.commit()
        return {"importadas": importadas, "erros": len(erros)}
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        job = db.get(ImportJob, UUID(job_id))
        if job:
            job.status = ImportStatus.ERRO.value
            job.erros = [{"motivo": str(exc)}]
            db.commit()
        raise
    finally:
        db.close()


@celery_app.task(name="app.workers.tasks.import_contacts_task")
def import_contacts_task(job_id: str, tenant_id: str, user_id: str, content: str, filename: str):
    """`content` chega em base64 (o broker Celery serializa em JSON, que não aceita bytes crus)."""
    set_current_tenant(UUID(tenant_id))
    set_current_user(UUID(user_id))
    db = SessionLocal()
    try:
        job = db.get(ImportJob, UUID(job_id))
        job.status = ImportStatus.PROCESSANDO.value
        db.flush()
        df = _read_table(base64.b64decode(content), filename)
        companies = CompanyRepository(db)
        contacts = ContactRepository(db)
        erros, importadas = [], 0
        for idx, row in df.iterrows():
            faltando = [c for c in CONTACT_REQUIRED if c not in df.columns or pd.isna(row.get(c))]
            if faltando:
                erros.append({"linha": int(idx) + 2, "motivo": f"Campos obrigatórios ausentes: {faltando}"})
                continue
            empresa = companies.get_by_cnpj(str(row["empresa"]).strip())
            if empresa is None:
                erros.append({"linha": int(idx) + 2, "motivo": "Empresa (CNPJ) não localizada"})
                continue
            contacts.add(Contact(
                company_id=empresa.id, nome=str(row["nome"]).strip(),
                email=str(row["email"]).strip(),
                cargo=str(row["cargo"]).strip() if "cargo" in df.columns and not pd.isna(row.get("cargo")) else None,
                telefone=str(row["telefone"]).strip() if "telefone" in df.columns and not pd.isna(row.get("telefone")) else None,
            ))
            importadas += 1
        job.total_linhas = int(len(df))
        job.importadas = importadas
        job.erros = erros
        job.status = ImportStatus.CONCLUIDO.value
        db.commit()
        return {"importadas": importadas, "erros": len(erros)}
    finally:
        db.close()


@celery_app.task(name="app.workers.tasks.import_lead_prospects_task")
def import_lead_prospects_task(job_id: str, tenant_id: str, user_id: str, content: str, filename: str):
    """`content` chega em base64 (o broker Celery serializa em JSON, que não aceita bytes crus)."""
    set_current_tenant(UUID(tenant_id))
    set_current_user(UUID(user_id))
    db = SessionLocal()
    try:
        job = db.get(ImportJob, UUID(job_id))
        job.status = ImportStatus.PROCESSANDO.value
        db.flush()
        df = _read_table(base64.b64decode(content), filename)
        leads = LeadProspectRepository(db)
        users = UserRepository(db)
        status_values = {s.value for s in LeadStatus}
        erros, importadas = [], 0
        for idx, row in df.iterrows():
            faltando = [c for c in LEAD_PROSPECT_REQUIRED if c not in df.columns or pd.isna(row.get(c))]
            if faltando:
                erros.append({"linha": int(idx) + 2, "motivo": f"Campos obrigatórios ausentes: {faltando}"})
                continue

            def opt_str(col):
                return str(row[col]).strip() if col in df.columns and not pd.isna(row.get(col)) else None

            def opt_float(col):
                val = opt_str(col)
                try:
                    return float(val) if val else None
                except ValueError:
                    return None

            pesquisador_id = UUID(user_id)
            email_col = opt_str("pesquisado_por")
            if email_col:
                pesquisador = users.get_by_email(email_col)
                if pesquisador is None:
                    erros.append({"linha": int(idx) + 2, "motivo": f"Pesquisador '{email_col}' não encontrado"})
                    continue
                pesquisador_id = pesquisador.id

            status_col = opt_str("status")
            status = status_col if status_col in status_values else LeadStatus.NOVO.value

            leads.add(LeadProspect(
                empresa=str(row["empresa"]).strip(),
                setor=opt_str("setor"), segmento=opt_str("segmento"),
                uf=(opt_str("uf") or "")[:2] or None,
                regiao=opt_str("regiao"),
                faixa_funcionarios=opt_str("faixa_funcionarios"),
                faturamento=opt_float("faturamento"),
                telefone=opt_str("telefone"), site=opt_str("site"), linkedin=opt_str("linkedin"),
                contato_sugerido=opt_str("contato_sugerido"), dor_sugerida=opt_str("dor_sugerida"),
                status=status, pesquisado_por=pesquisador_id,
            ))
            importadas += 1
        job.total_linhas = int(len(df))
        job.importadas = importadas
        job.erros = erros
        job.status = ImportStatus.CONCLUIDO.value
        db.commit()
        return {"importadas": importadas, "erros": len(erros)}
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        job = db.get(ImportJob, UUID(job_id))
        if job:
            job.status = ImportStatus.ERRO.value
            job.erros = [{"motivo": str(exc)}]
            db.commit()
        raise
    finally:
        db.close()


SEQUENCE_STEP_LABEL = {"ligacao": "Ligação", "email": "E-mail", "whatsapp": "WhatsApp", "followup": "Follow-up"}


def _resolve_responsavel(db, enrollment, owner) -> UUID:
    """Responsável da tarefa gerada: dono do negócio > dono da empresa > quem criou a sequência/cadência.

    `enrollment` é um SequenceEnrollment ou CadenceEnrollment e `owner` a Sequence/Cadence
    correspondente — ambos os pares têm o mesmo formato (company_id/deal_id, created_by).
    """
    if enrollment.deal_id:
        deal = db.get(Deal, enrollment.deal_id)
        if deal:
            return deal.responsavel_id
    if enrollment.company_id:
        company = db.get(Company, enrollment.company_id)
        if company and company.responsavel_id:
            return company.responsavel_id
    return owner.created_by


def _titulo_para_step(db, sequence: Sequence, step) -> str:
    base = SEQUENCE_STEP_LABEL.get(step.tipo, step.tipo)
    if step.template_id:
        template = db.get(EmailTemplate, step.template_id)
        if template:
            return f"{base} — {sequence.nome}: {template.nome}"
    return f"{base} — {sequence.nome}"


def _process_tenant_sequence_enrollments(tenant_id: UUID) -> int:
    set_current_tenant(tenant_id)
    db = SessionLocal()
    criadas = 0
    try:
        hoje = date.today()
        enrollments = db.execute(
            select(SequenceEnrollment)
            .join(Sequence, Sequence.id == SequenceEnrollment.sequence_id)
            .where(
                SequenceEnrollment.tenant_id == tenant_id,
                SequenceEnrollment.status == "ativa",
                Sequence.ativo.is_(True),
            )
        ).scalars().all()
        for enrollment in enrollments:
            sequence = enrollment.sequence
            steps = sorted(sequence.steps, key=lambda s: s.ordem)
            responsavel_id = _resolve_responsavel(db, enrollment, sequence)
            contact = resolve_contact(db, enrollment.contact_id, enrollment.deal_id)

            if (
                sequence.pausar_em_resposta and enrollment.step_atual > 0
                and contact and contact.email
                and has_active_email_integration(db, responsavel_id)
                and has_replied(db, responsavel_id, contact.email, enrollment.atualizado_em)
            ):
                enrollment.status = "pausada"
                enrollment.pausado_motivo = "resposta_recebida"
                continue

            dias_decorridos = (datetime.now(timezone.utc) - enrollment.iniciado_em).days
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
                        responsavel_id=responsavel_id,
                        company_id=enrollment.company_id, contact_id=enrollment.contact_id, deal_id=enrollment.deal_id,
                        data=hoje,
                    ))
                enrollment.step_atual += 1
                criadas += 1
            if enrollment.step_atual >= len(steps):
                enrollment.status = "concluida"
        db.commit()
    finally:
        db.close()
    return criadas


@celery_app.task(name="app.workers.tasks.process_due_sequence_steps")
def process_due_sequence_steps():
    """Varredura diária (Celery Beat) de sequence_enrollments ativos (RF010, §7.5).

    Roda cross-tenant: `sequences`/`sequence_enrollments` não têm política de RLS real no
    Postgres, o isolamento é aplicado em app/repositories/base.py via ContextVar — por isso
    é preciso trocar o tenant explicitamente a cada iteração, como no restante dos workers.
    """
    db = SessionLocal()
    try:
        tenant_ids = [t.id for t in db.execute(select(Tenant)).scalars().all()]
    finally:
        db.close()
    total_criadas = sum(_process_tenant_sequence_enrollments(tenant_id) for tenant_id in tenant_ids)
    return {"tarefas_criadas": total_criadas}


def _titulo_email_cadence(db, cadence: Cadence, step) -> str:
    template = db.get(EmailTemplate, step.template_id)
    nome_template = template.nome if template else "(modelo removido)"
    return f"E-mail — {cadence.nome}: {nome_template}"


def _process_tenant_cadence_enrollments(tenant_id: UUID) -> int:
    """Processa no máximo 1 e-mail por inscrição a cada rodada — diferente de Sequências,
    uma cadência de e-mail não deve "compensar" dias parados disparando vários e-mails de
    uma vez no mesmo dia (ruim para quem recebe); ela simplesmente atrasa a cadência inteira.

    Envio real via Microsoft Graph (`sequence_dispatch.send_step_email`) quando o
    responsável tem a conta Microsoft 365 conectada e há um contato com e-mail
    resolvível; caso contrário, cai para o comportamento antigo — cria uma Task
    (tipo=email) para o responsável enviar manualmente pelo modelo indicado.
    """
    set_current_tenant(tenant_id)
    db = SessionLocal()
    criadas = 0
    try:
        hoje = date.today()
        enrollments = db.execute(
            select(CadenceEnrollment)
            .join(Cadence, Cadence.id == CadenceEnrollment.cadence_id)
            .where(
                CadenceEnrollment.tenant_id == tenant_id,
                CadenceEnrollment.status == "ativa",
                Cadence.ativo.is_(True),
            )
        ).scalars().all()
        for enrollment in enrollments:
            cadence = enrollment.cadence
            steps = sorted(cadence.steps, key=lambda s: s.ordem)
            responsavel_id = _resolve_responsavel(db, enrollment, cadence)
            contact = resolve_contact(db, enrollment.contact_id, enrollment.deal_id)

            if (
                cadence.pausar_em_resposta and enrollment.step_atual > 0
                and contact and contact.email
                and has_active_email_integration(db, responsavel_id)
                and has_replied(db, responsavel_id, contact.email, enrollment.atualizado_em)
            ):
                enrollment.status = "pausada"
                enrollment.pausado_motivo = "resposta_recebida"
                continue

            dias_desde_ultimo = (datetime.now(timezone.utc) - enrollment.atualizado_em).days
            if enrollment.step_atual < len(steps) and steps[enrollment.step_atual].dias_espera <= dias_desde_ultimo:
                step = steps[enrollment.step_atual]
                enviado = False
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
                        tenant_id=tenant_id, titulo=_titulo_email_cadence(db, cadence, step), tipo="email",
                        responsavel_id=responsavel_id,
                        company_id=enrollment.company_id, contact_id=enrollment.contact_id, deal_id=enrollment.deal_id,
                        data=hoje,
                    ))
                enrollment.step_atual += 1
                criadas += 1
            if enrollment.step_atual >= len(steps):
                if cadence.criar_followup:
                    db.add(Task(
                        tenant_id=tenant_id, titulo=cadence.followup_titulo or f"Follow-up — {cadence.nome}",
                        tipo="followup", responsavel_id=responsavel_id,
                        company_id=enrollment.company_id, contact_id=enrollment.contact_id, deal_id=enrollment.deal_id,
                        data=hoje,
                    ))
                enrollment.status = "concluida"
        db.commit()
    finally:
        db.close()
    return criadas


@celery_app.task(name="app.workers.tasks.process_due_cadence_steps")
def process_due_cadence_steps():
    """Varredura diária (Celery Beat) de cadence_enrollments ativos (RF011, §7.6)."""
    db = SessionLocal()
    try:
        tenant_ids = [t.id for t in db.execute(select(Tenant)).scalars().all()]
    finally:
        db.close()
    total_criadas = sum(_process_tenant_cadence_enrollments(tenant_id) for tenant_id in tenant_ids)
    return {"tarefas_criadas": total_criadas}


def _condicoes_satisfeitas(condicoes: list[dict] | None, payload: dict) -> bool:
    for c in condicoes or []:
        valor_evento = payload.get(c["campo"])
        operador, valor_cond = c["operador"], c["valor"]
        if valor_evento is None:
            return False
        if operador == "igual a" and str(valor_evento) != str(valor_cond):
            return False
        if operador == "diferente de" and str(valor_evento) == str(valor_cond):
            return False
        if operador == "contém" and str(valor_cond).lower() not in str(valor_evento).lower():
            return False
        if operador in ("maior que", "menor que"):
            try:
                a, b = float(valor_evento), float(valor_cond)
            except (TypeError, ValueError):
                return False
            if operador == "maior que" and not (a > b):
                return False
            if operador == "menor que" and not (a < b):
                return False
    return True


def _entidade_fk_kwargs(payload: dict, entidade_ref: UUID) -> dict:
    """Mapeia o UUID genérico do evento pro FK certo de `Task` conforme quem disparou."""
    tipo = payload.get("_entidade_tipo")
    if tipo == "company":
        return {"company_id": entidade_ref}
    if tipo == "contact":
        company_id = payload.get("_company_id")
        return {"contact_id": entidade_ref, "company_id": UUID(company_id) if company_id else None}
    if tipo == "deal":
        company_id = payload.get("_company_id")
        return {"deal_id": entidade_ref, "company_id": UUID(company_id) if company_id else None}
    return {}


def _resolve_workflow_destinatario(db, tenant_id: UUID, destinatario: str | None, entidade_ref: UUID, payload: dict) -> UUID:
    """Resolve o usuário-alvo de uma ação de workflow.

    'Gestor comercial'/'Administrador' buscam por perfil; 'Responsável pelo registro'
    (default) busca o dono do negócio/empresa que disparou o evento. Sempre cai pra
    qualquer admin do tenant se a resolução específica não achar ninguém.
    """
    if destinatario == "Gestor comercial":
        u = db.execute(select(User).where(User.tenant_id == tenant_id, User.perfil == "gestor",
                                          User.status == "ativo")).scalars().first()
        if u:
            return u.id
    if destinatario in ("Administrador", "Gestor comercial"):
        u = db.execute(select(User).where(User.tenant_id == tenant_id, User.perfil == "admin",
                                          User.status == "ativo")).scalars().first()
        if u:
            return u.id
    if payload.get("_entidade_tipo") == "deal":
        deal = db.get(Deal, entidade_ref)
        if deal:
            return deal.responsavel_id
    company_id_str = str(entidade_ref) if payload.get("_entidade_tipo") == "company" else payload.get("_company_id")
    if company_id_str:
        company = db.get(Company, UUID(company_id_str))
        if company and company.responsavel_id:
            return company.responsavel_id
    admin = db.execute(select(User).where(User.tenant_id == tenant_id, User.perfil == "admin")).scalars().first()
    if admin:
        return admin.id
    raise RuntimeError("Não foi possível resolver um responsável para a ação")


def _execute_workflow_action(db, workflow: Workflow, action, entidade_ref: UUID, payload: dict) -> str:
    p = action.parametros or {}
    tenant_id = workflow.tenant_id

    if action.tipo_acao == "criar_tarefa":
        resp = _resolve_workflow_destinatario(db, tenant_id, p.get("destinatario"), entidade_ref, payload)
        db.add(Task(
            tenant_id=tenant_id, titulo=p.get("titulo") or f"Tarefa — {workflow.nome}",
            tipo=p.get("tipo_tarefa", "followup"), responsavel_id=resp,
            data=date.today() + timedelta(days=int(p.get("dias_apos", 0) or 0)),
            **_entidade_fk_kwargs(payload, entidade_ref),
        ))
        return "Tarefa criada"

    if action.tipo_acao == "enviar_email":
        template_id = p.get("template_id")
        template = db.get(EmailTemplate, UUID(template_id)) if template_id else None
        resp = _resolve_workflow_destinatario(db, tenant_id, "Responsável pelo registro", entidade_ref, payload)
        titulo = f"E-mail — {workflow.nome}" + (f": {template.nome}" if template else "")
        db.add(Task(
            tenant_id=tenant_id, titulo=titulo, tipo="email", responsavel_id=resp,
            data=date.today() + timedelta(days=int(p.get("dias_apos", 0) or 0)),
            **_entidade_fk_kwargs(payload, entidade_ref),
        ))
        return "E-mail agendado (sem envio automático configurado — vira tarefa)"

    if action.tipo_acao == "alterar_pipeline":
        stage_id = p.get("stage_id")
        if not stage_id:
            return "Sem etapa configurada — ação ignorada"
        deal = db.get(Deal, entidade_ref) if payload.get("_entidade_tipo") == "deal" else None
        if deal is None:
            return "Entidade não é um negócio — ação ignorada"
        stage = db.get(PipelineStage, UUID(stage_id))
        if stage is None or stage.pipeline_id != deal.pipeline_id:
            return "Etapa não pertence ao pipeline do negócio — ação ignorada"
        # Mutação direta (não usa DealService.move_stage): evita republicar `mudanca_etapa`
        # e criar um laço infinito quando o próprio gatilho do workflow é mudanca_etapa.
        deal.stage_id = stage.id
        if stage.probabilidade is not None:
            deal.probabilidade = stage.probabilidade
        return f"Negócio movido para a etapa \"{stage.nome}\""

    if action.tipo_acao == "notificar_usuario":
        resp = _resolve_workflow_destinatario(db, tenant_id, p.get("destinatario"), entidade_ref, payload)
        db.add(Task(
            tenant_id=tenant_id, titulo=p.get("mensagem") or f"Notificação — {workflow.nome}",
            tipo="followup", responsavel_id=resp, data=date.today(),
            **_entidade_fk_kwargs(payload, entidade_ref),
        ))
        return "Usuário notificado (sem canal de notificação real — vira tarefa)"

    if action.tipo_acao == "executar_enriquecimento":
        raise RuntimeError("Ação 'Executar enriquecimento' depende do módulo de IA (Fase 3), ainda não implementado")

    raise RuntimeError(f"Tipo de ação desconhecido: {action.tipo_acao}")


def _execute_workflow(db, workflow: Workflow, entidade_ref: UUID, payload: dict) -> None:
    resultados = []
    for action in sorted(workflow.actions, key=lambda a: a.ordem):
        try:
            detalhe = _execute_workflow_action(db, workflow, action, entidade_ref, payload)
            resultados.append({"acao": action.tipo_acao, "sucesso": True, "detalhe": detalhe})
        except Exception as exc:  # noqa: BLE001 — falha de 1 ação não deve derrubar as outras
            resultados.append({"acao": action.tipo_acao, "sucesso": False, "detalhe": str(exc)})
    resultado_geral = "sucesso" if all(r["sucesso"] for r in resultados) else "erro"
    db.add(WorkflowExecutionLog(
        tenant_id=workflow.tenant_id, workflow_id=workflow.id, workflow_nome=workflow.nome,
        entidade_ref=entidade_ref, resultado=resultado_geral, detalhes={"acoes": resultados},
    ))


@celery_app.task(name="app.workers.tasks.dispatch_workflow_event")
def dispatch_workflow_event(tenant_id: str, gatilho: str, entidade_ref: str, payload: dict):
    """Disparado por `app/services/workflow_events.py.publish_event()` depois que a transação
    de origem (Empresa/Contato/Negócio criado, mudança de etapa) já foi commitada."""
    set_current_tenant(UUID(tenant_id))
    db = SessionLocal()
    try:
        workflows = db.execute(
            select(Workflow).where(Workflow.tenant_id == UUID(tenant_id), Workflow.gatilho == gatilho,
                                   Workflow.ativo.is_(True))
        ).scalars().all()
        for workflow in workflows:
            if _condicoes_satisfeitas(workflow.condicoes, payload):
                _execute_workflow(db, workflow, UUID(entidade_ref), payload)
        db.commit()
        return {"workflows_avaliados": len(workflows)}
    finally:
        db.close()
