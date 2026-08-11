"""Repositórios de Sequências."""
from uuid import UUID

from sqlalchemy import select

from app.models.sequence import Sequence, SequenceEnrollment
from app.repositories.base import BaseRepository


class SequenceRepository(BaseRepository[Sequence]):
    model = Sequence

    def search_filter(self, termo: str):
        return Sequence.nome.ilike(f"%{termo}%")


class SequenceEnrollmentRepository(BaseRepository[SequenceEnrollment]):
    model = SequenceEnrollment

    def list_by_sequence(self, sequence_id: UUID) -> list[SequenceEnrollment]:
        stmt = self._base_query().where(SequenceEnrollment.sequence_id == sequence_id) \
            .order_by(SequenceEnrollment.iniciado_em.desc())
        return list(self.db.execute(stmt).scalars().all())

    def count_ativas(self, sequence_id: UUID) -> int:
        stmt = select(SequenceEnrollment).where(
            SequenceEnrollment.tenant_id == self._tenant_id(),
            SequenceEnrollment.sequence_id == sequence_id,
            SequenceEnrollment.status == "ativa",
        )
        return len(list(self.db.execute(stmt).scalars().all()))

    def list_ativas_ou_pausadas_para_cancelar(
        self, company_id: UUID | None, contact_id: UUID | None, deal_id: UUID | None,
    ) -> list[SequenceEnrollment]:
        """Inscrições ativas/pausadas atingidas por uma reunião marcada (ver
        sequence_dispatch.cancel_enrollments_on_meeting). Casa pelo alvo mais específico
        disponível — negócio > contato > empresa — pra não cancelar, por exemplo, a
        inscrição de outro contato/negócio da mesma empresa que não teve reunião marcada."""
        if deal_id:
            condicao = SequenceEnrollment.deal_id == deal_id
        elif contact_id:
            condicao = SequenceEnrollment.contact_id == contact_id
        elif company_id:
            condicao = SequenceEnrollment.company_id == company_id
        else:
            return []
        stmt = self._base_query().where(SequenceEnrollment.status.in_(("ativa", "pausada")), condicao)
        return list(self.db.execute(stmt).scalars().all())
