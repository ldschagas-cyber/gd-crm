"""Serviço de Sequências (RF010, §7.5)."""
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.context import get_current_user_id
from app.core.exceptions import NotFoundError
from app.models.company import Company
from app.models.contact import Contact
from app.models.deal import Deal
from app.models.sequence import Sequence, SequenceEnrollment, SequenceStep
from app.repositories.sequence import SequenceEnrollmentRepository, SequenceRepository
from app.schemas.common import PageParams
from app.schemas.sequence import SequenceCreate, SequenceEnrollmentCreate, SequenceStepIn, SequenceUpdate


class SequenceService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = SequenceRepository(db)
        self.enroll_repo = SequenceEnrollmentRepository(db)

    def _attach_inscritos_ativos(self, sequences: "list[Sequence]") -> "list[Sequence]":
        if not sequences:
            return sequences
        ids = [s.id for s in sequences]
        counts = dict(self.db.execute(
            select(SequenceEnrollment.sequence_id, func.count())
            .where(SequenceEnrollment.sequence_id.in_(ids), SequenceEnrollment.status == "ativa")
            .group_by(SequenceEnrollment.sequence_id)
        ).all())
        for s in sequences:
            s.inscritos_ativos = counts.get(s.id, 0)
        return sequences

    def list(self, params: PageParams, busca: str | None = None) -> "tuple[list[Sequence], int]":
        filters = []
        if busca:
            filters.append(self.repo.search_filter(busca))
        items, total = self.repo.list(*filters, offset=params.offset, limit=params.size, order_by=Sequence.nome)
        return self._attach_inscritos_ativos(items), total

    def get(self, sequence_id: UUID) -> Sequence:
        sequence = self.repo.get(sequence_id)
        if sequence is None:
            raise NotFoundError("Sequência não encontrada")
        self._attach_inscritos_ativos([sequence])
        return sequence

    def _build_steps(self, steps_in: "list[SequenceStepIn]") -> "list[SequenceStep]":
        return [
            SequenceStep(ordem=idx, dia_offset=s.dia_offset, tipo=s.tipo,
                        template_id=s.template_id, instrucoes=s.instrucoes)
            for idx, s in enumerate(steps_in)
        ]

    def create(self, data: SequenceCreate) -> Sequence:
        sequence = Sequence(
            nome=data.nome, ativo=data.ativo, pausar_em_resposta=data.pausar_em_resposta,
            created_by=get_current_user_id(), steps=self._build_steps(data.steps),
        )
        sequence = self.repo.add(sequence)
        self._attach_inscritos_ativos([sequence])
        return sequence

    def update(self, sequence_id: UUID, data: SequenceUpdate) -> Sequence:
        sequence = self.get(sequence_id)
        payload = data.model_dump(exclude_unset=True, exclude={"steps"})
        for field, value in payload.items():
            setattr(sequence, field, value)
        if data.steps is not None:
            sequence.steps = self._build_steps(data.steps)
        return self.repo.save(sequence)

    def clone(self, sequence_id: UUID) -> Sequence:
        original = self.get(sequence_id)
        clone = Sequence(
            nome=f"{original.nome} (cópia)", ativo=False, pausar_em_resposta=original.pausar_em_resposta,
            created_by=get_current_user_id(),
            steps=[
                SequenceStep(ordem=s.ordem, dia_offset=s.dia_offset, tipo=s.tipo,
                            template_id=s.template_id, instrucoes=s.instrucoes)
                for s in original.steps
            ],
        )
        clone = self.repo.add(clone)
        self._attach_inscritos_ativos([clone])
        return clone

    def delete(self, sequence_id: UUID) -> None:
        sequence = self.get(sequence_id)
        self.repo.delete(sequence)

    # ---- inscrições ---------------------------------------------------
    def _resolve_alvo(self, enrollment: SequenceEnrollment) -> SequenceEnrollment:
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

    def list_enrollments(self, sequence_id: UUID) -> "list[SequenceEnrollment]":
        self.get(sequence_id)  # 404 se a sequência não existe/não é do tenant
        enrollments = self.enroll_repo.list_by_sequence(sequence_id)
        return [self._resolve_alvo(e) for e in enrollments]

    def enroll(self, sequence_id: UUID, data: SequenceEnrollmentCreate) -> SequenceEnrollment:
        self.get(sequence_id)
        enrollment = SequenceEnrollment(
            sequence_id=sequence_id, company_id=data.company_id,
            contact_id=data.contact_id, deal_id=data.deal_id,
        )
        enrollment = self.enroll_repo.add(enrollment)
        return self._resolve_alvo(enrollment)
