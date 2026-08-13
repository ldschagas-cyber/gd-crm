"""Repositórios de Assinatura e AssinaturaEvento."""
from uuid import UUID

from app.models.subscription import Assinatura, AssinaturaEvento, AssinaturaStatus
from app.repositories.base import BaseRepository


class AssinaturaRepository(BaseRepository[Assinatura]):
    model = Assinatura

    def get_ativa_por_empresa(self, company_id: UUID) -> Assinatura | None:
        stmt = self._base_query().where(
            Assinatura.company_id == company_id, Assinatura.status == AssinaturaStatus.ATIVA.value,
        )
        return self.db.execute(stmt).scalars().first()


class AssinaturaEventoRepository(BaseRepository[AssinaturaEvento]):
    model = AssinaturaEvento

    def list_by_assinatura(self, assinatura_id: UUID) -> list[AssinaturaEvento]:
        items, _ = self.list(
            AssinaturaEvento.assinatura_id == assinatura_id, limit=1000,
            order_by=AssinaturaEvento.data_evento.desc(),
        )
        return items
