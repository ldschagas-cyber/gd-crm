"""Tarefas Celery: importação assíncrona de empresas e contatos (Excel/CSV) e automações."""
import base64
import io
import re
from datetime import date, datetime, timedelta
from uuid import UUID

import pandas as pd
from sqlalchemy import select

from app.core.celery_app import celery_app
from app.core.context import set_current_tenant, set_current_user
from app.core.database import SessionLocal
from app.core.text import dedupe_key
from app.models.call import Call
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
from app.services.company_dedupe import find_duplicate_company
from app.services.sequence_dispatch import (
    advance_due_steps, has_active_email_integration, has_replied, log_email_sent, render_template,
    resolve_company_id, resolve_contact, send_step_email,
)
from app.services.sequence_dispatch import _resolve_responsavel as resolve_sequence_responsavel
from app.services.workflow_events import publish_event

# cnpj não é mais obrigatório aqui: a cascata de dedupe (find_duplicate_company) cobre
# empresas sem CNPJ via domínio/nome+UF — sem isso, listas de prospecção sem CNPJ
# (comuns) não tinham proteção nenhuma contra duplicidade.
COMPANY_REQUIRED = ["razao_social", "cidade", "uf", "responsavel"]
# responsavel agora obrigatório: contato precisa nascer associado a alguém, e precisa
# bater com o responsável já cadastrado da empresa (ver import_contacts_task).
CONTACT_REQUIRED = ["nome", "empresa", "email", "responsavel"]
COMPANY_CONTACT_REQUIRED = [
    "empresa_razao_social", "empresa_cidade", "empresa_uf", "contato_nome", "contato_email", "responsavel",
]
LEAD_PROSPECT_REQUIRED = ["empresa"]


def _read_table(content: bytes, filename: str) -> pd.DataFrame:
    # dtype=str evita que o pandas infira colunas como cnpj/telefone como numéricas
    # (o que rebatizaria "11222333000144" para "11222333000144.0" e estouraria
    # o VARCHAR(14) do banco) e preserva zeros à esquerda.
    if filename.lower().endswith(".csv"):
        return pd.read_csv(io.BytesIO(content), dtype=str)
    return pd.read_excel(io.BytesIO(content), dtype=str)


def _looks_like_cnpj(value: str) -> bool:
    return len(re.sub(r"\D", "", value)) == 14


def _find_company_by_cnpj_or_name(companies: CompanyRepository, valor: str) -> Company | None:
    """Localiza empresa pela coluna 'empresa' de import_contacts_task: CNPJ (14 dígitos,
    com ou sem máscara) ou razão social (comparação normalizada, ver dedupe_key)."""
    if _looks_like_cnpj(valor):
        found = companies.get_by_cnpj(re.sub(r"\D", "", valor))
        if found:
            return found
    key = dedupe_key(valor)
    if not key:
        return None
    return next((c for c in companies.find_by_uf_not_deleted(None) if dedupe_key(c.razao_social) == key), None)


def _empresa_ja_cadastrada_erro(users: UserRepository, duplicate: Company) -> str:
    dono = users.get(duplicate.responsavel_id) if duplicate.responsavel_id else None
    detalhe = f": {dono.nome} ({dono.email})" if dono else ""
    return f"Empresa já cadastrada para outro responsável{detalhe}"


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
        users = UserRepository(db)
        erros, importadas = [], 0
        for idx, row in df.iterrows():
            faltando = [c for c in COMPANY_REQUIRED if c not in df.columns or pd.isna(row.get(c))]
            if faltando:
                erros.append({"linha": int(idx) + 2, "motivo": f"Campos obrigatórios ausentes: {faltando}"})
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

            # Empresa não pode nascer sem dono (trava decidida com o usuário) — coluna
            # "responsavel" traz o e-mail do usuário, mesmo padrão de "pesquisado_por"
            # na importação de Pesquisa de Leads, um pouco abaixo.
            responsavel_email = str(row["responsavel"]).strip()
            responsavel = users.get_by_email(responsavel_email)
            if responsavel is None:
                erros.append({"linha": int(idx) + 2, "motivo": f"Responsável '{responsavel_email}' não encontrado"})
                continue

            razao_social = str(row["razao_social"]).strip()
            uf = str(row["uf"]).strip()[:2]
            cnpj = opt_str("cnpj")
            site = opt_str("site")
            email = opt_str("email")

            # Cascata CNPJ -> domínio -> nome normalizado+UF (ver app/services/company_dedupe.py).
            duplicate = find_duplicate_company(repo, razao_social=razao_social, uf=uf, cnpj=cnpj, site=site, email=email)
            if duplicate is not None:
                if duplicate.responsavel_id == responsavel.id:
                    erros.append({"linha": int(idx) + 2, "motivo": "Empresa já cadastrada"})
                else:
                    erros.append({"linha": int(idx) + 2, "motivo": _empresa_ja_cadastrada_erro(users, duplicate)})
                continue

            repo.add(Company(
                razao_social=razao_social, cnpj=cnpj, cidade=str(row["cidade"]).strip(), uf=uf, site=site,
                segmento=opt_str("segmento"), telefone=opt_str("telefone"), email=email,
                porte=opt_str("porte"), num_funcionarios=opt_int("funcionarios"),
                faturamento_estimado=opt_float("faturamento"), origem=opt_str("origem"),
                responsavel_id=responsavel.id,
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
    """`content` chega em base64 (o broker Celery serializa em JSON, que não aceita bytes crus).

    Importa contatos pra empresas já cadastradas (coluna "empresa" aceita CNPJ ou razão
    social). Contato nunca tem dono independente da empresa: a coluna "responsavel" só
    serve pra *validar* que quem está importando conhece o responsável certo da empresa
    (trava do vendedor B não conseguir associar contato a uma empresa de outro dono) —
    o valor gravado em Contact.responsavel_id é sempre o da empresa, não o da coluna.
    """
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
        users = UserRepository(db)
        erros, importadas = [], 0
        for idx, row in df.iterrows():
            faltando = [c for c in CONTACT_REQUIRED if c not in df.columns or pd.isna(row.get(c))]
            if faltando:
                erros.append({"linha": int(idx) + 2, "motivo": f"Campos obrigatórios ausentes: {faltando}"})
                continue

            empresa = _find_company_by_cnpj_or_name(companies, str(row["empresa"]).strip())
            if empresa is None:
                erros.append({"linha": int(idx) + 2, "motivo": "Empresa não localizada (CNPJ ou razão social)"})
                continue

            responsavel_email = str(row["responsavel"]).strip()
            responsavel = users.get_by_email(responsavel_email)
            if responsavel is None:
                erros.append({"linha": int(idx) + 2, "motivo": f"Responsável '{responsavel_email}' não encontrado"})
                continue
            if empresa.responsavel_id != responsavel.id:
                erros.append({"linha": int(idx) + 2, "motivo": "Responsável informado não é o responsável desta empresa"})
                continue

            email = str(row["email"]).strip()
            if contacts.get_by_company_and_email(empresa.id, email) is None:
                contacts.add(Contact(
                    company_id=empresa.id, nome=str(row["nome"]).strip(), email=email,
                    cargo=str(row["cargo"]).strip() if "cargo" in df.columns and not pd.isna(row.get("cargo")) else None,
                    telefone=str(row["telefone"]).strip() if "telefone" in df.columns and not pd.isna(row.get("telefone")) else None,
                    responsavel_id=empresa.responsavel_id,
                ))
            importadas += 1  # conta como sucesso mesmo quando o contato já existia (reaproveitado)
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


@celery_app.task(name="app.workers.tasks.import_companies_contacts_task")
def import_companies_contacts_task(job_id: str, tenant_id: str, user_id: str, content: str, filename: str):
    """`content` chega em base64 (o broker Celery serializa em JSON, que não aceita bytes crus).

    Importação combinada: cada linha traz empresa (colunas `empresa_*`) e contato
    (colunas `contato_*`) juntos — caso comum de listas de prospecção (ex.: Top 80), que
    já vêm com as duas pontas. Uma única coluna `responsavel` vale pros dois, já que
    contato nunca tem dono independente da empresa.

    Se a empresa já existir (cascata CNPJ -> domínio -> nome+UF, ver
    app/services/company_dedupe.py) e for do mesmo responsável, reaproveita (caminho
    feliz: "contato novo pra empresa já cadastrada"). Se já existir com responsável
    diferente, rejeita a linha inteira — não anexa contato à conta de outro vendedor.
    """
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
        users = UserRepository(db)
        erros, importadas = [], 0
        for idx, row in df.iterrows():
            faltando = [c for c in COMPANY_CONTACT_REQUIRED if c not in df.columns or pd.isna(row.get(c))]
            if faltando:
                erros.append({"linha": int(idx) + 2, "motivo": f"Campos obrigatórios ausentes: {faltando}"})
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

            responsavel_email = str(row["responsavel"]).strip()
            responsavel = users.get_by_email(responsavel_email)
            if responsavel is None:
                erros.append({"linha": int(idx) + 2, "motivo": f"Responsável '{responsavel_email}' não encontrado"})
                continue

            razao_social = str(row["empresa_razao_social"]).strip()
            uf = str(row["empresa_uf"]).strip()[:2]
            cnpj = opt_str("empresa_cnpj")
            site = opt_str("empresa_site")
            email_empresa = opt_str("empresa_email")
            contato_email = str(row["contato_email"]).strip()

            duplicate = find_duplicate_company(
                companies, razao_social=razao_social, uf=uf, cnpj=cnpj, site=site,
                email=email_empresa, contato_email=contato_email,
            )
            if duplicate is not None and duplicate.responsavel_id != responsavel.id:
                erros.append({"linha": int(idx) + 2, "motivo": _empresa_ja_cadastrada_erro(users, duplicate)})
                continue

            if duplicate is not None:
                empresa = duplicate  # mesmo responsável -> reaproveita, caminho feliz
            else:
                empresa = companies.add(Company(
                    razao_social=razao_social, cnpj=cnpj, cidade=str(row["empresa_cidade"]).strip(), uf=uf,
                    site=site, segmento=opt_str("empresa_segmento"), telefone=opt_str("empresa_telefone"),
                    email=email_empresa, porte=opt_str("empresa_porte"),
                    num_funcionarios=opt_int("empresa_funcionarios"),
                    faturamento_estimado=opt_float("empresa_faturamento"),
                    origem=opt_str("empresa_origem"), responsavel_id=responsavel.id, created_by=UUID(user_id),
                ))

            if contacts.get_by_company_and_email(empresa.id, contato_email) is None:
                contacts.add(Contact(
                    company_id=empresa.id, nome=str(row["contato_nome"]).strip(), email=contato_email,
                    cargo=opt_str("contato_cargo"), telefone=opt_str("contato_telefone"),
                    responsavel_id=empresa.responsavel_id,
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
                cidade=opt_str("cidade"),
                uf=(opt_str("uf") or "")[:2] or None,
                regiao=opt_str("regiao"),
                faixa_funcionarios=opt_str("faixa_funcionarios"),
                faixa_faturamento=opt_str("faixa_faturamento"),
                origem=opt_str("origem"),
                telefone=opt_str("telefone"), site=opt_str("site"), linkedin=opt_str("linkedin"),
                email=opt_str("email"),
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


def _process_tenant_sequence_enrollments(tenant_id: UUID) -> int:
    set_current_tenant(tenant_id)
    db = SessionLocal()
    criadas = 0
    try:
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
            contact = resolve_contact(db, enrollment.contact_id, enrollment.deal_id)

            # Checagem de resposta só roda pra quem tem pausar_em_resposta ligado — não só
            # por causa do custo de bater no Graph pra cada enrollment ativo, mas porque isso
            # também garante que o gatilho `resposta_recebida` (publish_event abaixo) só dispara
            # uma vez por resposta: assim que dispara, o enrollment sai de "ativa" (vira
            # "pausada") e some deste loop, então não há re-checagem no próximo dia pra
            # republicar o mesmo evento. Rodar essa checagem pra todo enrollment ativo,
            # independente do pausar_em_resposta, exigiria um campo próprio de "já notificado"
            # pra evitar disparar o mesmo evento repetidamente enquanto o enrollment continua
            # ativo — fora do escopo desta tarefa.
            if sequence.pausar_em_resposta and enrollment.step_atual > 0 and contact and contact.email:
                responsavel_id = resolve_sequence_responsavel(db, enrollment, sequence)
                if (
                    has_active_email_integration(db, responsavel_id)
                    and has_replied(db, responsavel_id, contact.email, enrollment.atualizado_em)
                ):
                    publish_event(db, "resposta_recebida", contact.id, {
                        "cargo": contact.cargo, "canal": "email",
                        "_entidade_tipo": "contact",
                        "_company_id": str(contact.company_id) if contact.company_id else None,
                    })
                    enrollment.status = "pausada"
                    enrollment.pausado_motivo = "resposta_recebida"
                    continue

            criadas += advance_due_steps(db, tenant_id, enrollment)
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


def _resolve_workflow_entidades(payload: dict, entidade_ref: UUID) -> tuple[UUID | None, UUID | None, UUID | None]:
    """Mapeia o UUID genérico do evento pros 3 FKs (company/contact/deal) conforme quem disparou."""
    tipo = payload.get("_entidade_tipo")
    company_id_raw = entidade_ref if tipo == "company" else payload.get("_company_id")
    company_id = UUID(str(company_id_raw)) if company_id_raw else None
    contact_id = entidade_ref if tipo == "contact" else None
    deal_id = entidade_ref if tipo == "deal" else None
    return company_id, contact_id, deal_id


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
        company_id, contact_id, deal_id = _resolve_workflow_entidades(payload, entidade_ref)
        contact = resolve_contact(db, contact_id, deal_id)
        company_id = resolve_company_id(db, company_id, deal_id, contact)
        enviado = False
        if template and contact and contact.email and company_id:
            assunto, corpo = render_template(template, contact, db.get(Company, company_id), db.get(User, resp))
            enviado = send_step_email(db, resp, contact, assunto, corpo)
            if enviado:
                log_email_sent(db, tenant_id, company_id, contact.id, deal_id, assunto, resp)
        if enviado:
            return "E-mail enviado automaticamente"
        # Fallback (comportamento antigo): sem contato com e-mail, modelo, ou integração
        # conectada, vira tarefa manual — igual ao que Sequência/Cadência já fazem.
        titulo = f"E-mail — {workflow.nome}" + (f": {template.nome}" if template else "")
        db.add(Task(
            tenant_id=tenant_id, titulo=titulo, tipo="email", responsavel_id=resp,
            data=date.today() + timedelta(days=int(p.get("dias_apos", 0) or 0)),
            **_entidade_fk_kwargs(payload, entidade_ref),
        ))
        return "Sem contato/integração disponível — criada tarefa manual"

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

    if action.tipo_acao == "inscrever_em_sequencia":
        sequence_id = p.get("sequence_id")
        sequence = db.get(Sequence, UUID(sequence_id)) if sequence_id else None
        if sequence is None or not sequence.ativo:
            return "Sequência não configurada ou inativa — ação ignorada"
        company_id, contact_id, deal_id = _resolve_workflow_entidades(payload, entidade_ref)
        ja_inscrito = db.execute(
            select(SequenceEnrollment).where(
                SequenceEnrollment.sequence_id == sequence.id,
                SequenceEnrollment.status == "ativa",
                SequenceEnrollment.company_id == company_id,
                SequenceEnrollment.contact_id == contact_id,
                SequenceEnrollment.deal_id == deal_id,
            )
        ).scalars().first()
        if ja_inscrito:
            return "Já inscrito nesta sequência — ação ignorada"
        enrollment = SequenceEnrollment(
            tenant_id=tenant_id, sequence_id=sequence.id,
            company_id=company_id, contact_id=contact_id, deal_id=deal_id,
        )
        db.add(enrollment)
        db.flush()
        db.refresh(enrollment)
        # Etapa(s) com dia_offset <= 0 viram tarefa (ou e-mail) já aqui, em vez
        # de esperar a próxima varredura diária do Celery Beat (6h).
        advance_due_steps(db, tenant_id, enrollment)
        return f"Inscrito na sequência \"{sequence.nome}\""

    if action.tipo_acao == "executar_enriquecimento":
        # Reaproveita o mesmo serviço de IA do Dossiê Comercial (resumo executivo + próxima
        # ação sugerida) — diferente de app/services/lead_enrichment.py (usado no botão
        # "Enriquecer com IA" da Pesquisa de Leads), que só monta uma sugestão pro vendedor
        # revisar e aceitar manualmente e não se aplica aqui: opera sobre LeadProspect, uma
        # entidade que não existe nos eventos de Workflow (Empresa/Contato/Negócio já
        # cadastrados). CompanyAiService.regenerate_resumo já grava direto no registro —
        # é o mesmo caminho usado automaticamente a cada evento relevante da timeline
        # (ver app/services/company_ai.py:schedule_if_relevant), então aplicar aqui também
        # sem exigir clique em "Aplicar" é consistente com o resto do sistema.
        company_id, _, _ = _resolve_workflow_entidades(payload, entidade_ref)
        if not company_id:
            return "Sem empresa associada ao evento — ação ignorada"
        from app.services.company_ai import CompanyAiService
        CompanyAiService(db).regenerate_resumo(company_id)
        return "Resumo executivo e próxima ação atualizados via IA"

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


@celery_app.task(name="app.workers.tasks.transcribe_call_recording_task")
def transcribe_call_recording_task(call_id: str, recording_url: str):
    """Disparado por `app/services/twilio_voice.py:record_recording_completed`
    depois que a gravação da ligação termina (RecordingStatus == completed)."""
    db = SessionLocal()
    try:
        call = db.get(Call, UUID(call_id))
        if call is None:
            return
        set_current_tenant(call.tenant_id)
        set_current_user(call.user_id)
        from app.services.assemblyai_transcription import transcribe_and_submit
        transcribe_and_submit(db, call, recording_url)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@celery_app.task(name="app.workers.tasks.regenerate_company_summary")
def regenerate_company_summary(tenant_id: str, company_id: str):
    """Disparado por `app/services/company_ai.py.schedule_resumo_regeneration()` depois que
    um evento relevante da timeline (ou uma edição do Dossiê) já foi commitado."""
    set_current_tenant(UUID(tenant_id))
    db = SessionLocal()
    try:
        from app.services.company_ai import CompanyAiService, clear_resumo_debounce
        # Libera a janela de debounce logo no início: eventos que chegarem durante
        # a chamada de IA (alguns segundos) abrem um novo ciclo e serão capturados
        # por uma regeneração seguinte, em vez de serem engolidos por esta.
        clear_resumo_debounce(UUID(tenant_id), UUID(company_id))
        CompanyAiService(db).regenerate_resumo(UUID(company_id))
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@celery_app.task(name="app.workers.tasks.gerar_faturamento_mensal")
def gerar_faturamento_mensal():
    """Faturamento recorrente mensal (RF-FAT / RN-F01). Cross-tenant como os demais
    workers: troca o tenant explicitamente e comita por tenant. Idempotente (RN-F02) —
    reprocessar a mesma competência não duplica cobranças. Dispara o pedido de NF ao
    contador por tenant (usa o remetente configurado; sem config, apenas não envia)."""
    db = SessionLocal()
    try:
        tenant_ids = [t.id for t in db.execute(select(Tenant)).scalars().all()]
    finally:
        db.close()

    from app.services.faturamento import FaturamentoService
    resultados: dict[str, dict] = {}
    for tenant_id in tenant_ids:
        set_current_tenant(tenant_id)
        db = SessionLocal()
        try:
            res = FaturamentoService(db).gerar()
            db.commit()
            resultados[str(tenant_id)] = {
                "competencia": res.competencia, "geradas": res.geradas,
                "ja_existentes": res.ja_existentes, "nf_solicitadas": res.nf_solicitadas,
            }
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
    return resultados
