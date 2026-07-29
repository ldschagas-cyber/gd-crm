"""Repositórios de Workflows."""
from uuid import UUID

from app.models.workflow import Workflow, WorkflowExecutionLog
from app.repositories.base import BaseRepository


class WorkflowRepository(BaseRepository[Workflow]):
    model = Workflow

    def search_filter(self, termo: str):
        return Workflow.nome.ilike(f"%{termo}%")

    def list_ativos_por_gatilho(self, gatilho: str) -> list[Workflow]:
        items, _ = self.list(Workflow.gatilho == gatilho, Workflow.ativo.is_(True), limit=1000)
        return items


class WorkflowExecutionLogRepository(BaseRepository[WorkflowExecutionLog]):
    model = WorkflowExecutionLog

    def list_by_workflow(self, workflow_id: UUID) -> list[WorkflowExecutionLog]:
        stmt = self._base_query().where(WorkflowExecutionLog.workflow_id == workflow_id) \
            .order_by(WorkflowExecutionLog.executado_em.desc()).limit(50)
        return list(self.db.execute(stmt).scalars().all())
