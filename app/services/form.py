"""Serviço de Formulários: CRUD, KPIs e recepção pública de envios (item 9.8)."""
from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.context import set_current_tenant
from app.core.exceptions import ConflictError, NotFoundError
from app.models.company import Company, CompanyStatus
from app.models.contact import Contact
from app.models.form import Form, FormStatus, FormSubmission, PostSubmitAction
from app.repositories.company import CompanyRepository
from app.repositories.contact import ContactRepository
from app.repositories.form import FormRepository, FormSubmissionRepository
from app.repositories.site_visit import SiteVisitRepository
from app.schemas.common import PageParams
from app.schemas.form import (
    FormCreate, FormKpis, FormRead, FormSubmissionRead, FormUpdate, PublicFormSubmit,
)


class FormService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = FormRepository(db)
        self.submissions = FormSubmissionRepository(db)
        self.site_visits = SiteVisitRepository(db)

    def _envios_30d(self, form_id: UUID, since: datetime) -> int:
        _, total = self.submissions.list(
            self.submissions.model.form_id == form_id,
            self.submissions.model.created_at >= since,
            offset=0, limit=1,
        )
        return total

    def to_read(self, form: Form, since: datetime) -> FormRead:
        envios = self._envios_30d(form.id, since)
        conversao = None
        if form.pagina:
            visitas = self.site_visits.count_by_path_since(form.pagina, since)
            if visitas > 0:
                conversao = round(envios / visitas * 100, 1)
        return FormRead(
            id=form.id, nome=form.nome, pagina=form.pagina, status=form.status,
            campos=form.campos, campos_personalizados=form.campos_personalizados,
            post_submit_action=form.post_submit_action,
            created_at=form.created_at, updated_at=form.updated_at,
            envios_30d=envios, conversao_pct=conversao,
        )

    def list(self) -> list[FormRead]:
        since = datetime.now(timezone.utc) - timedelta(days=30)
        items, _ = self.repo.list(offset=0, limit=1000, order_by=Form.updated_at.desc())
        return [self.to_read(f, since) for f in items]

    def _get_orm(self, form_id: UUID) -> Form:
        form = self.repo.get(form_id)
        if form is None:
            raise NotFoundError("Formulário não encontrado")
        return form

    def get(self, form_id: UUID) -> FormRead:
        since = datetime.now(timezone.utc) - timedelta(days=30)
        return self.to_read(self._get_orm(form_id), since)

    def create(self, data: FormCreate) -> FormRead:
        payload = data.model_dump()
        payload["status"] = data.status.value
        payload["post_submit_action"] = data.post_submit_action.value
        form = Form(**payload)
        form = self.repo.add(form)
        return self.get(form.id)

    def update(self, form_id: UUID, data: FormUpdate) -> FormRead:
        form = self._get_orm(form_id)
        payload = data.model_dump(exclude_unset=True)
        for key in ("status", "post_submit_action"):
            if payload.get(key) is not None:
                payload[key] = payload[key].value
        for field, value in payload.items():
            setattr(form, field, value)
        form = self.repo.save(form)
        return self.get(form.id)

    def list_submissions(self, form_id: UUID, params: PageParams) -> "tuple[list[FormSubmissionRead], int]":
        # anotação em string: `list` já é sombreado pelo método list() desta classe
        self._get_orm(form_id)  # valida existência/tenant
        items, total = self.submissions.list_by_form(form_id, params.offset, params.size)
        return [FormSubmissionRead.model_validate(s, from_attributes=True) for s in items], total

    def kpis(self) -> FormKpis:
        since = datetime.now(timezone.utc) - timedelta(days=30)
        forms, total_forms = self.repo.list(offset=0, limit=1000)
        ativos = sum(1 for f in forms if f.status == FormStatus.ATIVO.value)

        envios_total = 0
        visitas_total = 0
        for f in forms:
            envios_total += self._envios_30d(f.id, since)
            if f.pagina:
                visitas_total += self.site_visits.count_by_path_since(f.pagina, since)
        taxa = round(envios_total / visitas_total * 100, 1) if visitas_total > 0 else None

        _, leads_gerados = self.submissions.list(
            self.submissions.model.created_at >= since,
            self.submissions.model.company_id.is_not(None),
            self.submissions.model.duplicado.is_(False),
            offset=0, limit=1,
        )
        return FormKpis(
            formularios_ativos=ativos, formularios_total=total_forms,
            envios_30d=envios_total, taxa_conversao_media=taxa, leads_gerados_30d=leads_gerados,
        )

    # ---- recepção pública (sem auth) -----------------------------------------
    def submit_public(self, form_id: UUID, data: PublicFormSubmit, ip: str | None) -> FormSubmissionRead:
        form = self.repo.get_public(form_id)
        if form is None:
            raise NotFoundError("Formulário não encontrado")
        if form.status != FormStatus.ATIVO.value:
            raise ConflictError("Este formulário não está aceitando envios no momento")

        set_current_tenant(form.tenant_id)

        company_id = None
        contact_id = None
        duplicado = False
        empresa_nome = (data.valores.get("empresa") or "").strip()

        if form.post_submit_action == PostSubmitAction.CRIAR_LEAD.value and empresa_nome:
            companies = CompanyRepository(self.db)
            company = None
            cnpj = data.valores.get("cnpj")
            if cnpj:
                company = companies.get_by_cnpj(str(cnpj).strip())
            if company is None:
                company = companies.get_by_name(empresa_nome)
            if company is not None:
                duplicado = True
            else:
                company = companies.add(Company(
                    razao_social=empresa_nome,
                    cnpj=str(cnpj).strip() if cnpj else None,
                    site=data.valores.get("site"),
                    cidade=data.valores.get("cidade"),
                    uf=(data.valores.get("uf") or None) and str(data.valores["uf"]).strip()[:2],
                    segmento=data.valores.get("segmento"),
                    porte=data.valores.get("porte"),
                    origem=data.valores.get("origem") or f"Formulário: {form.nome}",
                    status=CompanyStatus.LEAD.value,
                ))
            company_id = company.id

            nascimento = None
            if data.valores.get("nascimento"):
                try:
                    nascimento = date.fromisoformat(str(data.valores["nascimento"])[:10])
                except ValueError:
                    nascimento = None

            contact = ContactRepository(self.db).add(Contact(
                company_id=company.id, nome=data.nome, email=data.email,
                cargo=data.valores.get("cargo"), telefone=data.valores.get("telefone"),
                whatsapp=data.valores.get("whatsapp"), linkedin=data.valores.get("linkedin"),
                data_nascimento=nascimento,
            ))
            contact_id = contact.id

        submission = self.submissions.add(FormSubmission(
            form_id=form.id, nome=data.nome, email=data.email, valores=data.valores,
            ip=ip, company_id=company_id, contact_id=contact_id, duplicado=duplicado,
        ))
        return FormSubmissionRead.model_validate(submission, from_attributes=True)
