"""Serviço de tarefas: CRUD e conclusão com registro em timeline."""
from datetime import date, datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.context import get_current_user_id
from app.core.exceptions import NotFoundError
from app.models.task import ResultadoLigacao, Task, TaskStatus
from app.models.timeline import TimelineType
from app.repositories.task import TaskRepository
from app.schemas.common import PageParams
from app.schemas.task import TaskCreate, TaskSendEmail, TaskUpdate
from app.services.graph_client import GraphClient
from app.services.timeline import TimelineService


RESULTADO_LIGACAO_LABEL = {
    ResultadoLigacao.ATENDEU.value: "Atendeu",
    ResultadoLigacao.RECADO_CAIXA_POSTAL.value: "Deixou recado / caixa postal",
    ResultadoLigacao.NAO_ATENDEU.value: "Não atendeu",
    ResultadoLigacao.OCUPADO.value: "Ocupado",
    ResultadoLigacao.NUMERO_ERRADO.value: "Número errado / inexistente",
    ResultadoLigacao.RECUSOU_FALAR.value: "Recusou falar",
}


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

    def complete(self, task_id: UUID, resultado_ligacao: ResultadoLigacao | None = None,
                observacoes: str | None = None) -> Task:
        task = self.get(task_id)
        task.status = TaskStatus.CONCLUIDA.value
        task.concluida_em = datetime.now(timezone.utc)
        if resultado_ligacao is not None:
            task.resultado_ligacao = resultado_ligacao.value
        task = self.repo.save(task)
        if task.company_id:
            meta = {"resultado_ligacao": task.resultado_ligacao} if task.resultado_ligacao else None
            self.timeline.registrar(task.company_id, TimelineType.TAREFA.value,
                                    f"Tarefa concluída: {task.titulo}", observacoes,
                                    deal_id=task.deal_id, contact_id=task.contact_id, meta=meta)
        return task

    def uncomplete(self, task_id: UUID) -> Task:
        """Reverte uma conclusão feita por engano — sem contrapartida na timeline
        (o registro de conclusão original fica como está; reabrir não é um evento
        novo digno de nota, só desfaz o estado)."""
        task = self.get(task_id)
        task.status = TaskStatus.PENDENTE.value
        task.concluida_em = None
        return self.repo.save(task)

    def send_email(self, task_id: UUID, data: TaskSendEmail) -> Task:
        """Envio manual de e-mail pela fila de execução — reaproveita a mesma
        conta Microsoft 365 (Graph) já usada pelo envio automático de
        Sequências. Levanta ConflictError (via GraphClient) se o responsável
        não tiver a integração conectada; o painel da fila deve checar
        `GET /me/integrations/email` antes e não chamar isso nesse caso."""
        task = self.get(task_id)
        user_id = get_current_user_id()
        GraphClient(self.db).send_mail(user_id, data.destinatario, data.assunto, data.corpo)

        task.status = TaskStatus.CONCLUIDA.value
        task.concluida_em = datetime.now(timezone.utc)
        task = self.repo.save(task)
        if task.company_id:
            self.timeline.registrar(
                task.company_id, TimelineType.EMAIL.value, data.assunto, data.corpo,
                deal_id=task.deal_id, contact_id=task.contact_id,
                meta={"enviado": True, "destinatario": data.destinatario, "via_fila_tarefas": True},
            )
        return task

    def delete(self, task_id: UUID) -> None:
        task = self.get(task_id)
        self.repo.delete(task)
