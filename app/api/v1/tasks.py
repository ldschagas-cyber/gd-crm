"""Rotas de tarefas, incluindo exportação."""
import csv
import io
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.common import Page, PageParams
from app.schemas.task import TaskCreate, TaskRead, TaskUpdate
from app.services.task import TaskService

router = APIRouter(prefix="/tasks", tags=["Tarefas"])

EXPORT_COLUMNS = ["titulo", "tipo", "data", "hora", "prioridade", "status"]


@router.get("", response_model=Page[TaskRead])
def list_tasks(
    params: PageParams = Depends(),
    responsavel_id: UUID | None = None,
    status_: str | None = Query(None, alias="status"),
    tipo: str | None = None,
    company_id: UUID | None = None,
    prioridade: str | None = None,
    busca: str | None = None,
    data_inicio: date | None = None,
    data_fim: date | None = None,
    deal_id: UUID | None = None,
    contact_id: UUID | None = None,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items, total = TaskService(db).list(
        params, responsavel_id, status_, tipo, company_id, prioridade, busca, data_inicio, data_fim, deal_id,
        contact_id,
    )
    return Page(items=items, total=total, page=params.page, size=params.size)


@router.post("", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
def create_task(data: TaskCreate, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return TaskService(db).create(data)


@router.get("/export")
def export_tasks(
    responsavel_id: UUID | None = None,
    status_: str | None = Query(None, alias="status"),
    tipo: str | None = None,
    company_id: UUID | None = None,
    prioridade: str | None = None,
    busca: str | None = None,
    data_inicio: date | None = None,
    data_fim: date | None = None,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items = TaskService(db).list_for_export(
        responsavel_id, status_, tipo, company_id, prioridade, busca, data_inicio, data_fim,
    )
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(EXPORT_COLUMNS)
    for t in items:
        writer.writerow([
            t.titulo, t.tipo, t.data.isoformat(), t.hora.isoformat() if t.hora else "",
            t.prioridade, t.status,
        ])
    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=tarefas.csv"},
    )


@router.get("/{task_id}", response_model=TaskRead)
def get_task(task_id: UUID, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return TaskService(db).get(task_id)


@router.put("/{task_id}", response_model=TaskRead)
def update_task(task_id: UUID, data: TaskUpdate, _: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    return TaskService(db).update(task_id, data)


@router.patch("/{task_id}/complete", response_model=TaskRead)
def complete_task(task_id: UUID, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return TaskService(db).complete(task_id)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: UUID, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    TaskService(db).delete(task_id)
    return None
