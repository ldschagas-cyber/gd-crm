"""Metas de Venda — quantidade e valor por vendedor e por equipe, por mês.

A meta é definida por vendedor por mês (SalesTarget); o realizado é lido ao vivo
dos negócios ganhos (Deal status=ganho, data_fechamento no mês), no mesmo espírito
das Metas do Funil — nada de escrita manual do realizado. A meta da equipe é a soma
das metas dos seus vendedores. Ver docs/PLANO_METAS_VENDA.md.
"""
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.context import get_current_tenant
from app.core.exceptions import AppException
from app.models.deal import Deal, DealStatus
from app.models.sales_target import SalesTarget
from app.models.team import Team
from app.models.user import User
from app.repositories.sales_target import SalesTargetRepository
from app.repositories.team import TeamRepository
from app.repositories.user import UserRepository
from app.schemas.metas_venda import (
    EquipeResumo,
    MetasVendaResumo,
    SalesTargetInput,
    VendedorMetaRow,
)


def _status(real: float, meta: float | None) -> str | None:
    """ok >= 100% da meta, atenção >= 70%, crítico abaixo. None = sem meta definida."""
    if meta is None:
        return None
    if meta <= 0 or real >= meta:
        return "ok"
    if real >= meta * 0.7:
        return "atencao"
    return "critico"


class MetasVendaService:
    def __init__(self, db: Session):
        self.db = db
        self.tenant_id = get_current_tenant()
        self.users = UserRepository(db)
        self.teams = TeamRepository(db)
        self.targets = SalesTargetRepository(db)

    # ---- período -----------------------------------------------------------
    def _mes_bounds(self, mes: str) -> tuple[datetime, datetime]:
        try:
            year, month = (int(p) for p in mes.split("-"))
            if not 1 <= month <= 12:
                raise ValueError
        except ValueError:
            raise AppException("Mês inválido — use o formato AAAA-MM")
        start = datetime(year, month, 1, tzinfo=timezone.utc)
        end = (
            datetime(year + 1, 1, 1, tzinfo=timezone.utc)
            if month == 12
            else datetime(year, month + 1, 1, tzinfo=timezone.utc)
        )
        return start, end

    def _realizado_por_vendedor(self, start: datetime, end: datetime) -> dict[UUID, tuple[int, float]]:
        """Negócios ganhos no mês, agrupados por responsável: (quantidade, soma do valor)."""
        rows = self.db.execute(
            select(
                Deal.responsavel_id,
                func.count(),
                func.coalesce(func.sum(Deal.valor_previsto), 0),
            )
            .where(
                Deal.tenant_id == self.tenant_id,
                Deal.status == DealStatus.GANHO.value,
                Deal.data_fechamento >= start,
                Deal.data_fechamento < end,
            )
            .group_by(Deal.responsavel_id)
        ).all()
        return {rid: (qtd, float(valor)) for rid, qtd, valor in rows}

    # ---- resumo ------------------------------------------------------------
    def resumo(self, mes: str) -> MetasVendaResumo:
        start, end = self._mes_bounds(mes)
        realizado = self._realizado_por_vendedor(start, end)

        targets, _ = self.targets.list(SalesTarget.mes == mes, limit=100_000)
        target_by_user = {t.user_id: t for t in targets}

        users, _ = self.users.list(limit=1000, order_by=User.nome)
        teams, _ = self.teams.list(limit=1000, order_by=Team.nome)
        user_by_id = {u.id: u for u in users}

        def build_row(u: User) -> VendedorMetaRow:
            tg = target_by_user.get(u.id)
            meta_qtd = tg.meta_qtd if tg else None
            meta_valor = float(tg.meta_valor) if tg and tg.meta_valor is not None else None
            r_qtd, r_valor = realizado.get(u.id, (0, 0.0))
            return VendedorMetaRow(
                user_id=u.id, nome=u.nome, perfil=u.perfil, team_id=u.team_id,
                meta_qtd=meta_qtd, meta_valor=meta_valor,
                realizado_qtd=r_qtd, realizado_valor=round(r_valor, 2),
                status_qtd=_status(r_qtd, meta_qtd), status_valor=_status(r_valor, meta_valor),
            )

        def has_dado(u: User) -> bool:
            r_qtd, r_valor = realizado.get(u.id, (0, 0.0))
            return u.id in target_by_user or r_qtd > 0 or r_valor > 0

        equipes: list[EquipeResumo] = []
        for team in teams:
            # Todo membro da equipe aparece (mesmo zerado) — o gestor precisa enxergar
            # o time inteiro, não só quem já vendeu.
            membros = [u for u in users if u.team_id == team.id]
            vendedores = [build_row(u) for u in membros]
            gestor = user_by_id.get(team.gestor_id) if team.gestor_id else None
            equipes.append(self._equipe_resumo(team.id, team.nome, gestor.nome if gestor else None, vendedores))

        # Vendedores sem equipe: só os que têm meta ou realizado (evita listar todo
        # admin/visualizador que nunca vende).
        sem_equipe_users = [u for u in users if u.team_id is None and has_dado(u)]
        if sem_equipe_users:
            vendedores = [build_row(u) for u in sem_equipe_users]
            equipes.append(self._equipe_resumo(None, "Sem equipe", None, vendedores))

        total_meta_qtd = sum(e.meta_qtd for e in equipes)
        total_meta_valor = round(sum(e.meta_valor for e in equipes), 2)
        total_real_qtd = sum(e.realizado_qtd for e in equipes)
        total_real_valor = round(sum(e.realizado_valor for e in equipes), 2)

        return MetasVendaResumo(
            periodo=mes, equipes=equipes,
            total_meta_qtd=total_meta_qtd, total_meta_valor=total_meta_valor,
            total_realizado_qtd=total_real_qtd, total_realizado_valor=total_real_valor,
        )

    @staticmethod
    def _equipe_resumo(team_id, nome, gestor_nome, vendedores: list[VendedorMetaRow]) -> EquipeResumo:
        meta_qtd = sum(v.meta_qtd or 0 for v in vendedores)
        meta_valor = round(sum(v.meta_valor or 0 for v in vendedores), 2)
        real_qtd = sum(v.realizado_qtd for v in vendedores)
        real_valor = round(sum(v.realizado_valor for v in vendedores), 2)
        return EquipeResumo(
            team_id=team_id, nome=nome, gestor_nome=gestor_nome,
            meta_qtd=meta_qtd, meta_valor=meta_valor,
            realizado_qtd=real_qtd, realizado_valor=real_valor,
            status_qtd=_status(real_qtd, meta_qtd if meta_qtd else None) or "ok",
            status_valor=_status(real_valor, meta_valor if meta_valor else None) or "ok",
            vendedores=vendedores,
        )

    # ---- edição das metas do mês ------------------------------------------
    def set_targets(self, mes: str, items: list[SalesTargetInput]) -> MetasVendaResumo:
        self._mes_bounds(mes)  # valida o formato do mês
        for item in items:
            existing = self.targets.get_by_user_mes(item.user_id, mes)
            vazio = item.meta_qtd is None and item.meta_valor is None
            if vazio:
                if existing:
                    self.targets.delete(existing)
                continue
            if existing:
                existing.meta_qtd = item.meta_qtd
                existing.meta_valor = item.meta_valor
                self.targets.save(existing)
            else:
                self.targets.add(SalesTarget(
                    user_id=item.user_id, mes=mes,
                    meta_qtd=item.meta_qtd, meta_valor=item.meta_valor,
                ))
        return self.resumo(mes)
