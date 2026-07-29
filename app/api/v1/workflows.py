"""Rotas de Workflows (RF018, §7.9)."""
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.common import Page, PageParams
from app.schemas.workflow import WorkflowCreate, WorkflowExecutionLogRead, WorkflowRead, WorkflowUpdate
from app.services.workflow import WorkflowService

router = APIRouter(prefix="/workflows", tags=["Workflows"])


@router.get("", response_model=Page[WorkflowRead])
def list_workflows(params: PageParams = Depends(), busca: str | None = None,
                    _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    items, total = WorkflowService(db).list(params, busca)
    return Page(items=items, total=total, page=params.page, size=params.size)


@router.post("", response_model=WorkflowRead, status_code=status.HTTP_201_CREATED)
def create_workflow(data: WorkflowCreate, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return WorkflowService(db).create(data)


@router.get("/{workflow_id}", response_model=WorkflowRead)
def get_workflow(workflow_id: UUID, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return WorkflowService(db).get(workflow_id)


@router.put("/{workflow_id}", response_model=WorkflowRead)
def update_workflow(workflow_id: UUID, data: WorkflowUpdate, _: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    return WorkflowService(db).update(workflow_id, data)


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workflow(workflow_id: UUID, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    WorkflowService(db).delete(workflow_id)


@router.get("/{workflow_id}/logs", response_model=list[WorkflowExecutionLogRead])
def list_workflow_logs(workflow_id: UUID, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return WorkflowService(db).list_logs(workflow_id)
