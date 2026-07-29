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
