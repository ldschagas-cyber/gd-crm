"""Repositório de Contratos."""
from datetime import date
from uuid import UUID

from sqlalchemy import extract, func, select

from app.models.contract import Contrato, ContratoStatus
from app.repositories.base import BaseRepository


class ContratoRepository(BaseRepository[Contrato]):
    model = Contrato

    def proximo_numero(self, ano: int) -> str:
        stmt = select(func.count()).select_from(
            self._base_query().where(extract("year", Contrato.created_at) == ano).subquery()
        )
        seq = self.db.execute(stmt).scalar_one() + 1
        return f"CTR-{ano}-{seq:03d}"

    def list_ativos(self) -> list[Contrato]:
        stmt = self._base_query().where(Contrato.status == ContratoStatus.ATIVO.value)
        return list(self.db.execute(stmt).scalars().all())

    def get_ativo_por_empresa(self, company_id: UUID) -> Contrato | None:
        stmt = self._base_query().where(
            Contrato.company_id == company_id, Contrato.status == ContratoStatus.ATIVO.value
        )
        return self.db.execute(stmt).scalars().first()
