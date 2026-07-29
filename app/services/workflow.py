"""Serviço de Workflows (RF018, §7.9) — CRUD; a execução mora em app/workers/tasks.py."""
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.workflow import Workflow, WorkflowAction, WorkflowExecutionLog
from app.repositories.workflow import WorkflowExecutionLogRepository, WorkflowRepository
from app.schemas.common import PageParams
from app.schemas.workflow import WorkflowActionIn, WorkflowCreate, WorkflowUpdate


class WorkflowService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = WorkflowRepository(db)
        self.log_repo = WorkflowExecutionLogRepository(db)

    def list(self, params: PageParams, busca: str | None = None) -> "tuple[list[Workflow], int]":
        filters = []
        if busca:
            filters.append(self.repo.search_filter(busca))
        return self.repo.list(*filters, offset=params.offset, limit=params.size, order_by=Workflow.nome)

    def get(self, workflow_id: UUID) -> Workflow:
        workflow = self.repo.get(workflow_id)
        if workflow is None:
            raise NotFoundError("Workflow não encontrado")
        return workflow

    def _build_actions(self, actions_in: "list[WorkflowActionIn]") -> "list[WorkflowAction]":
        return [
            WorkflowAction(ordem=idx, tipo_acao=a.tipo_acao, parametros=a.parametros)
            for idx, a in enumerate(actions_in)
        ]

    def create(self, data: WorkflowCreate) -> Workflow:
        workflow = Workflow(
            nome=data.nome, gatilho=data.gatilho, ativo=data.ativo,
            condicoes=[c.model_dump() for c in data.condicoes],
            actions=self._build_actions(data.actions),
        )
        return self.repo.add(workflow)

    def update(self, workflow_id: UUID, data: WorkflowUpdate) -> Workflow:
        workflow = self.get(workflow_id)
        payload = data.model_dump(exclude_unset=True, exclude={"actions", "condicoes"})
        for field, value in payload.items():
            setattr(workflow, field, value)
        if data.condicoes is not None:
            workflow.condicoes = [c.model_dump() for c in data.condicoes]
        if data.actions is not None:
            workflow.actions = self._build_actions(data.actions)
        return self.repo.save(workflow)

    def delete(self, workflow_id: UUID) -> None:
        # As execuções já registradas ficam (workflow_id vira NULL, nome fica congelado no
        # log) — só a definição do workflow some, por design (ver WorkflowExecutionLog).
        workflow = self.get(workflow_id)
        self.repo.delete(workflow)

    def list_logs(self, workflow_id: UUID) -> "list[WorkflowExecutionLog]":
        self.get(workflow_id)  # 404 se o workflow não existe/não é do tenant
        return self.log_repo.list_by_workflow(workflow_id)
