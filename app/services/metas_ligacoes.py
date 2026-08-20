"""Metas de Ligações — progresso por vendedor na semana e no mês correntes.

Realizado = tarefas tipo=ligacao concluídas por vendedor (mesma fonte que o
dashboard do vendedor já usa). Meta é fixa por semana/mês (colunas em User). O
progresso é sempre relativo a "agora" — semana e mês correntes, no molde das Metas
de Pesquisa. Ver docs/PLANO_METAS_VENDA.md.
"""
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.context import get_current_tenant
from app.models.task import Task, TaskStatus, TaskType
from app.models.user import User
from app.repositories.user import UserRepository
from app.schemas.metas_ligacoes import MetaLigacoesResponse, MetaLigacoesRow


class MetasLigacoesService:
    def __init__(self, db: Session):
        self.db = db
        self.tenant_id = get_current_tenant()
        self.users = UserRepository(db)

    def _contagem_desde(self, desde: datetime) -> dict[UUID, int]:
        rows = self.db.execute(
            select(Task.responsavel_id, func.count())
            .where(
                Task.tenant_id == self.tenant_id,
                Task.tipo == TaskType.LIGACAO.value,
                Task.status == TaskStatus.CONCLUIDA.value,
                Task.concluida_em >= desde,
            )
            .group_by(Task.responsavel_id)
        ).all()
        return {rid: c for rid, c in rows}

    def progresso(self) -> MetaLigacoesResponse:
        now = datetime.now(timezone.utc)
        inicio_semana = (now - timedelta(days=now.weekday())).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        inicio_mes = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        por_semana = self._contagem_desde(inicio_semana)
        por_mes = self._contagem_desde(inicio_mes)

        users, _ = self.users.list(limit=1000, order_by=User.nome)
        rows = []
        for user in users:
            ligacoes_semana = por_semana.get(user.id, 0)
            ligacoes_mes = por_mes.get(user.id, 0)
            # Some da lista quem não tem meta e não fez nenhuma ligação — não é um
            # vendedor relevante pra essa tela.
            if user.meta_ligacoes_semanal is None and user.meta_ligacoes_mensal is None \
                    and ligacoes_semana == 0 and ligacoes_mes == 0:
                continue
            rows.append(MetaLigacoesRow(
                user_id=user.id, nome=user.nome,
                ligacoes_semana=ligacoes_semana, meta_semanal=user.meta_ligacoes_semanal,
                ligacoes_mes=ligacoes_mes, meta_mensal=user.meta_ligacoes_mensal,
            ))
        rows.sort(key=lambda r: -r.ligacoes_semana)
        return MetaLigacoesResponse(rows=rows)
