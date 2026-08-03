"""Serviço de tarefas: CRUD e conclusão com registro em timeline."""
from datetime import date, datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.task import Task, TaskStatus
from app.models.timeline import TimelineType
from app.repositories.task import TaskRepository
from app.schemas.common import PageParams
from app.schemas.task import TaskCreate, TaskUpdate
from app.services.timeline import TimelineService


class TaskService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = TaskRepository(db)
        self.timeline = TimelineService(db)

    def list(self, params: PageParams, responsavel_id: UUID | None = None,
             status: str | None = None, tipo: str | None = None,
             company_id: UUID | None = None, prioridade: str | None = None,
             busca: str | None = None, data_inicio: date | None = None,
             data_fim: date | None = None, deal_id: UUID | None = None,
             contact_id: UUID | None = None) -> tuple[list[Task], int]:
        filters = self._filters(responsavel_id, status, tipo, company_id, prioridade, busca,
                                data_inicio, data_fim, deal_id, contact_id)
        return self.repo.list(*filters, offset=params.offset, limit=params.size,
                              order_by=Task.data)

    def list_for_export(self, responsavel_id: UUID | None = None, status: str | None = None,
                        tipo: str | None = None, company_id: UUID | None = None,
                        prioridade: str | None = None, busca: str | None = None,
                        data_inicio: date | None = None, data_fim: date | None = None,
                        deal_id: UUID | None = None, contact_id: UUID | None = None) -> "list[Task]":
        # anotação em string: `list` já é sombreado pelo método list() desta classe
        filters = self._filters(responsavel_id, status, tipo, company_id, prioridade, busca,
                                data_inicio, data_fim, deal_id, contact_id)
        items, _ = self.repo.list(*filters, offset=0, limit=1_000_000, order_by=Task.data)
        return items

    def _filters(self, responsavel_id, status, tipo, company_id, prioridade, busca,
                 data_inicio=None, data_fim=None, deal_id=None, contact_id=None):
        filters = []
        if responsavel_id:
            filters.append(Task.responsavel_id == responsavel_id)
        if status:
            filters.append(Task.status == status)
        if tipo:
            filters.append(Task.tipo == tipo)
        if company_id:
            filters.append(Task.company_id == company_id)
        if deal_id:
            filters.append(Task.deal_id == deal_id)
        if contact_id:
            filters.append(Task.contact_id == contact_id)
        if prioridade:
            filters.append(Task.prioridade == prioridade)
        if busca:
            filters.append(self.repo.search_filter(busca))
        if data_inicio:
            filters.append(Task.data >= data_inicio)
        if data_fim:
            filters.append(Task.data <= data_fim)
        return filters

    def get(self, task_id: UUID) -> Task:
        task = self.repo.get(task_id)
        if task is None:
            raise NotFoundError("Tarefa não encontrada")
        return task

    def create(self, data: TaskCreate) -> Task:
        payload = data.model_dump()
        payload["tipo"] = data.tipo.value
        payload["prioridade"] = data.prioridade.value
        task = Task(**payload)
        return self.repo.add(task)

    def update(self, task_id: UUID, data: TaskUpdate) -> Task:
        task = self.get(task_id)
        payload = data.model_dump(exclude_unset=True)
        for key in ("tipo", "prioridade", "status"):
            if key in payload and payload[key] is not None:
                payload[key] = payload[key].value
        for field, value in payload.items():
            setattr(task, field, value)
        return self.repo.save(task)

    def complete(self, task_id: UUID) -> Task:
        task = self.get(task_id)
        task.status = TaskStatus.CONCLUIDA.value
        task.concluida_em = datetime.now(timezone.utc)
        task = self.repo.save(task)
        if task.company_id:
            self.timeline.registrar(task.company_id, TimelineType.TAREFA.value,
                                    f"Tarefa concluída: {task.titulo}",
                                    deal_id=task.deal_id, contact_id=task.contact_id)
        return task

    def delete(self, task_id: UUID) -> None:
        task = self.get(task_id)
        self.repo.delete(task)
