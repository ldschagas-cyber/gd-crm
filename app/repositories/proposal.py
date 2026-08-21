"""Repositório de Propostas."""
from datetime import date
from uuid import UUID

from sqlalchemy import extract, func, select

from app.models.proposal import Proposta, PropostaStatus
from app.repositories.base import BaseRepository


class PropostaRepository(BaseRepository[Proposta]):
    model = Proposta

    def proximo_numero(self, ano: int) -> str:
        """Sequência por tenant/ano: PROP-<ano>-<seq>. Conta as propostas do ano no
        tenant corrente e soma 1 (o filtro de tenant vem do _base_query)."""
        stmt = select(func.count()).select_from(
            self._base_query().where(extract("year", Proposta.created_at) == ano).subquery()
        )
        seq = self.db.execute(stmt).scalar_one() + 1
        return f"PROP-{ano}-{seq:03d}"

    def margem_por_vendedor(self, inicio: date, fim: date):
        """Retorna (vendedor_id, qtd_propostas, desconto_medio, desconto_max) por vendedor
        no período (RF-DSH-04), ignorando rascunhos."""
        stmt = (
            select(
                Proposta.vendedor_id,
                func.count().label("qtd"),
                func.coalesce(func.avg(Proposta.desconto_pct_total), 0).label("media"),
                func.coalesce(func.max(Proposta.desconto_pct_total), 0).label("maximo"),
            )
            .where(Proposta.tenant_id == self._tenant_id())
            .where(Proposta.created_at >= inicio, Proposta.created_at <= fim)
            .where(Proposta.status != PropostaStatus.RASCUNHO.value)
            .group_by(Proposta.vendedor_id)
        )
        return list(self.db.execute(stmt).all())

    def desconto_medio(self, inicio: date, fim: date):
        """Margem cedida: desconto % médio das propostas criadas no período (dashboard)."""
        stmt = (
            select(func.coalesce(func.avg(Proposta.desconto_pct_total), 0))
            .where(Proposta.tenant_id == self._tenant_id())
            .where(Proposta.created_at >= inicio, Proposta.created_at <= fim)
            .where(Proposta.status != PropostaStatus.RASCUNHO.value)
        )
        return self.db.execute(stmt).scalar_one()
