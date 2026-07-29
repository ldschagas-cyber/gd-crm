"""Serviço de Cadências (RF011, §7.6)."""
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.context import get_current_user_id
from app.core.exceptions import NotFoundError
from app.models.cadence import Cadence, CadenceEnrollment, CadenceStep
from app.models.company import Company
from app.models.contact import Contact
from app.models.deal import Deal
from app.repositories.cadence import CadenceEnrollmentRepository, CadenceRepository
from app.schemas.cadence import CadenceCreate, CadenceEnrollmentCreate, CadenceStepIn, CadenceUpdate
from app.schemas.common import PageParams


class CadenceService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = CadenceRepository(db)
        self.enroll_repo = CadenceEnrollmentRepository(db)

    def _attach_inscritos_ativos(self, cadences: "list[Cadence]") -> "list[Cadence]":
        if not cadences:
            return cadences
        ids = [c.id for c in cadences]
        counts = dict(self.db.execute(
            select(CadenceEnrollment.cadence_id, func.count())
            .where(CadenceEnrollment.cadence_id.in_(ids), CadenceEnrollment.status == "ativa")
            .group_by(CadenceEnrollment.cadence_id)
        ).all())
        for c in cadences:
            c.inscritos_ativos = counts.get(c.id, 0)
        return cadences

    def list(self, params: PageParams, busca: str | None = None) -> "tuple[list[Cadence], int]":
        filters = []
        if busca:
            filters.append(self.repo.search_filter(busca))
        items, total = self.repo.list(*filters, offset=params.offset, limit=params.size, order_by=Cadence.nome)
        return self._attach_inscritos_ativos(items), total

    def get(self, cadence_id: UUID) -> Cadence:
        cadence = self.repo.get(cadence_id)
        if cadence is None:
            raise NotFoundError("Cadência não encontrada")
        self._attach_inscritos_ativos([cadence])
        return cadence

    def _build_steps(self, steps_in: "list[CadenceStepIn]") -> "list[CadenceStep]":
        return [
            CadenceStep(ordem=idx, dias_espera=s.dias_espera, template_id=s.template_id)
            for idx, s in enumerate(steps_in)
        ]

    def create(self, data: CadenceCreate) -> Cadence:
        cadence = Cadence(
            nome=data.nome, ativo=data.ativo, pausar_em_resposta=data.pausar_em_resposta,
            criar_followup=data.criar_followup, followup_titulo=data.followup_titulo,
            created_by=get_current_user_id(), steps=self._build_steps(data.steps),
        )
        cadence = self.repo.add(cadence)
        self._attach_inscritos_ativos([cadence])
        return cadence

    def update(self, cadence_id: UUID, data: CadenceUpdate) -> Cadence:
        cadence = self.get(cadence_id)
        payload = data.model_dump(exclude_unset=True, exclude={"steps"})
        for field, value in payload.items():
            setattr(cadence, field, value)
        if data.steps is not None:
            cadence.steps = self._build_steps(data.steps)
        return self.repo.save(cadence)

    def clone(self, cadence_id: UUID) -> Cadence:
        original = self.get(cadence_id)
        clone = Cadence(
            nome=f"{original.nome} (cópia)", ativo=False, pausar_em_resposta=original.pausar_em_resposta,
            criar_followup=original.criar_followup, followup_titulo=original.followup_titulo,
            created_by=get_current_user_id(),
            steps=[
                CadenceStep(ordem=s.ordem, dias_espera=s.dias_espera, template_id=s.template_id)
                for s in original.steps
            ],
        )
        clone = self.repo.add(clone)
        self._attach_inscritos_ativos([clone])
        return clone

    def delete(self, cadence_id: UUID) -> None:
        cadence = self.get(cadence_id)
        self.repo.delete(cadence)

    # ---- inscrições ---------------------------------------------------
    def _resolve_alvo(self, enrollment: CadenceEnrollment) -> CadenceEnrollment:
        if enrollment.deal_id:
            deal = self.db.get(Deal, enrollment.deal_id)
            enrollment.alvo_nome = deal.nome if deal else "(negócio removido)"
            enrollment.alvo_tipo = "Negócio"
        elif enrollment.contact_id:
            contact = self.db.get(Contact, enrollment.contact_id)
            enrollment.alvo_nome = contact.nome if contact else "(contato removido)"
            enrollment.alvo_tipo = "Contato"
        else:
            company = self.db.get(Company, enrollment.company_id)
            enrollment.alvo_nome = (company.nome_fantasia or company.razao_social) if company else "(empresa removida)"
            enrollment.alvo_tipo = "Empresa"
        return enrollment

    def list_enrollments(self, cadence_id: UUID) -> "list[CadenceEnrollment]":
        self.get(cadence_id)  # 404 se a cadência não existe/não é do tenant
        enrollments = self.enroll_repo.list_by_cadence(cadence_id)
        return [self._resolve_alvo(e) for e in enrollments]

    def enroll(self, cadence_id: UUID, data: CadenceEnrollmentCreate) -> CadenceEnrollment:
        self.get(cadence_id)
        enrollment = CadenceEnrollment(
            cadence_id=cadence_id, company_id=data.company_id,
            contact_id=data.contact_id, deal_id=data.deal_id,
        )
        enrollment = self.enroll_repo.add(enrollment)
        return self._resolve_alvo(enrollment)
