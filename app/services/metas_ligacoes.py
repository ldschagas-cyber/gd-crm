"""Metas de Ligações — meta por mês (semanal e mensal) por vendedor.

A meta é definida por vendedor por mês (CallTarget); o realizado é lido ao vivo das
tarefas tipo=ligacao concluídas (mesma fonte do dashboard do vendedor). O bloco
mensal usa o mês consultado; o semanal usa a semana corrente e só é relevante
quando o mês consultado é o mês de hoje. Ver docs/PLANO_METAS_VENDA.md.
"""
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.context import get_current_tenant
from app.core.exceptions import AppException
from app.models.call_target import CallTarget
from app.models.task import Task, TaskStatus, TaskType
from app.models.user import User
from app.repositories.call_target import CallTargetRepository
from app.repositories.user import UserRepository
from app.schemas.metas_ligacoes import CallTargetInput, MetaLigacoesResponse, MetaLigacoesRow


class MetasLigacoesService:
    def __init__(self, db: Session):
        self.db = db
        self.tenant_id = get_current_tenant()
        self.users = UserRepository(db)
        self.targets = CallTargetRepository(db)

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

    def _contagem(self, desde: datetime, ate: datetime | None = None) -> dict[UUID, int]:
        filters = [
            Task.tenant_id == self.tenant_id,
            Task.tipo == TaskType.LIGACAO.value,
            Task.status == TaskStatus.CONCLUIDA.value,
            Task.concluida_em >= desde,
        ]
        if ate is not None:
            filters.append(Task.concluida_em < ate)
        rows = self.db.execute(
            select(Task.responsavel_id, func.count()).where(*filters).group_by(Task.responsavel_id)
        ).all()
        return {rid: c for rid, c in rows}

    def progresso(self, mes: str) -> MetaLigacoesResponse:
        start, end = self._mes_bounds(mes)
        now = datetime.now(timezone.utc)
        mes_corrente = mes == now.strftime("%Y-%m")

        por_mes = self._contagem(start, end)
        if mes_corrente:
            inicio_semana = (now - timedelta(days=now.weekday())).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            por_semana = self._contagem(inicio_semana)
        else:
            por_semana = {}

        targets, _ = self.targets.list(CallTarget.mes == mes, limit=100_000)
        target_by_user = {t.user_id: t for t in targets}

        users, _ = self.users.list(limit=1000, order_by=User.nome)
        rows = []
        for user in users:
            tg = target_by_user.get(user.id)
            ligacoes_mes = por_mes.get(user.id, 0)
            ligacoes_semana = por_semana.get(user.id, 0)
            # Some da lista quem não tem meta e não fez nenhuma ligação no período.
            if tg is None and ligacoes_mes == 0 and ligacoes_semana == 0:
                continue
            rows.append(MetaLigacoesRow(
                user_id=user.id, nome=user.nome, perfil=user.perfil,
                ligacoes_semana=ligacoes_semana, meta_semanal=tg.meta_semanal if tg else None,
                ligacoes_mes=ligacoes_mes, meta_mensal=tg.meta_mensal if tg else None,
            ))
        rows.sort(key=lambda r: -r.ligacoes_mes)
        return MetaLigacoesResponse(periodo=mes, mes_corrente=mes_corrente, rows=rows)

    def set_targets(self, mes: str, items: list[CallTargetInput]) -> MetaLigacoesResponse:
        self._mes_bounds(mes)  # valida o formato do mês
        for item in items:
            existing = self.targets.get_by_user_mes(item.user_id, mes)
            vazio = item.meta_semanal is None and item.meta_mensal is None
            if vazio:
                if existing:
                    self.targets.delete(existing)
                continue
            if existing:
                existing.meta_semanal = item.meta_semanal
                existing.meta_mensal = item.meta_mensal
                self.targets.save(existing)
            else:
                self.targets.add(CallTarget(
                    user_id=item.user_id, mes=mes,
                    meta_semanal=item.meta_semanal, meta_mensal=item.meta_mensal,
                ))
        return self.progresso(mes)
