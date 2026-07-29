"""Repositórios de Cadências."""
from uuid import UUID

from app.models.cadence import Cadence, CadenceEnrollment
from app.repositories.base import BaseRepository


class CadenceRepository(BaseRepository[Cadence]):
    model = Cadence

    def search_filter(self, termo: str):
        return Cadence.nome.ilike(f"%{termo}%")


class CadenceEnrollmentRepository(BaseRepository[CadenceEnrollment]):
    model = CadenceEnrollment

    def list_by_cadence(self, cadence_id: UUID) -> list[CadenceEnrollment]:
        stmt = self._base_query().where(CadenceEnrollment.cadence_id == cadence_id) \
            .order_by(CadenceEnrollment.iniciado_em.desc())
        return list(self.db.execute(stmt).scalars().all())
