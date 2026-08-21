"""Repositórios de Cobrança e Categoria financeira."""
from datetime import date
from uuid import UUID

from sqlalchemy import func, select, update

from app.models.billing import Cobranca, CobrancaStatus
from app.models.finance_category import CategoriaFinanceira
from app.repositories.base import BaseRepository


class CobrancaRepository(BaseRepository[Cobranca]):
    model = Cobranca

    def get_por_contrato_competencia(self, contrato_id: UUID, competencia: str) -> Cobranca | None:
        """Idempotência do faturamento (RN-F02): já existe cobrança deste contrato/competência?"""
        stmt = self._base_query().where(
            Cobranca.contrato_id == contrato_id, Cobranca.competencia == competencia
        )
        return self.db.execute(stmt).scalars().first()

    def list_por_competencia(self, competencia: str) -> list[Cobranca]:
        stmt = self._base_query().where(Cobranca.competencia == competencia).order_by(Cobranca.vencimento)
        return list(self.db.execute(stmt).scalars().all())

    def list_sem_nf_por_competencia(self, competencia: str) -> list[Cobranca]:
        stmt = self._base_query().where(
            Cobranca.competencia == competencia,
            Cobranca.nf_solicitada_em.is_(None),
            Cobranca.nf_numero.is_(None),
            Cobranca.status != CobrancaStatus.CANCELADA.value,
        ).order_by(Cobranca.vencimento)
        return list(self.db.execute(stmt).scalars().all())

    def marcar_vencidas(self, hoje: date) -> int:
        """RF-CAR-03: cobrança aberta com vencimento < hoje passa a `vencida`.
        Retorna quantas linhas foram atualizadas."""
        stmt = (
            update(Cobranca)
            .where(Cobranca.tenant_id == self._tenant_id())
            .where(Cobranca.status == CobrancaStatus.ABERTA.value)
            .where(Cobranca.vencimento < hoje)
            .values(status=CobrancaStatus.VENCIDA.value)
        )
        result = self.db.execute(stmt)
        return result.rowcount or 0

    def list_por_status(self, *status: str, limit: int = 20) -> list[Cobranca]:
        stmt = self._base_query().where(Cobranca.status.in_(status)).order_by(
            Cobranca.vencimento
        ).limit(limit)
        return list(self.db.execute(stmt).scalars().all())

    def count_por_status(self, *status: str) -> int:
        stmt = select(func.count()).select_from(
            self._base_query().where(Cobranca.status.in_(status)).subquery()
        )
        return self.db.execute(stmt).scalar_one()

    def soma_por_status(self, *status: str, venc_inicio: date | None = None,
                        venc_fim: date | None = None) -> float:
        stmt = (
            select(func.coalesce(func.sum(Cobranca.valor - Cobranca.valor_recebido), 0))
            .where(Cobranca.tenant_id == self._tenant_id())
            .where(Cobranca.status.in_(status))
        )
        if venc_inicio is not None:
            stmt = stmt.where(Cobranca.vencimento >= venc_inicio)
        if venc_fim is not None:
            stmt = stmt.where(Cobranca.vencimento <= venc_fim)
        return float(self.db.execute(stmt).scalar_one())


class CategoriaFinanceiraRepository(BaseRepository[CategoriaFinanceira]):
    model = CategoriaFinanceira

    def list_por_tipo(self, tipo: str) -> list[CategoriaFinanceira]:
        stmt = self._base_query().where(CategoriaFinanceira.tipo == tipo).order_by(CategoriaFinanceira.nome)
        return list(self.db.execute(stmt).scalars().all())

    def count_por_tipo(self, tipo: str) -> int:
        stmt = select(func.count()).select_from(
            self._base_query().where(CategoriaFinanceira.tipo == tipo).subquery()
        )
        return self.db.execute(stmt).scalar_one()
