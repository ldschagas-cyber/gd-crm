"""Rotas de pipelines, etapas e board (kanban)."""
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models.user import User, UserRole
from app.schemas.common import Page, PageParams
from app.schemas.pipeline import (
    BoardResponse, PipelineCreate, PipelineRead, PipelineUpdate, StageCreate, StageRead,
)
from app.services.pipeline import PipelineService

router = APIRouter(prefix="/pipelines", tags=["Pipelines"])
gestor = require_roles(UserRole.ADMIN.value, UserRole.GESTOR.value)


@router.get("", response_model=Page[PipelineRead])
def list_pipelines(params: PageParams = Depends(), _: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    items, total = PipelineService(db).list(params)
    return Page(items=items, total=total, page=params.page, size=params.size)


@router.post("", response_model=PipelineRead, status_code=status.HTTP_201_CREATED)
def create_pipeline(data: PipelineCreate, _: User = Depends(gestor), db: Session = Depends(get_db)):
    return PipelineService(db).create(data)


@router.get("/{pipeline_id}", response_model=PipelineRead)
def get_pipeline(pipeline_id: UUID, _: User = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    return PipelineService(db).get(pipeline_id)


@router.put("/{pipeline_id}", response_model=PipelineRead)
def update_pipeline(pipeline_id: UUID, data: PipelineUpdate, _: User = Depends(gestor),
                    db: Session = Depends(get_db)):
    return PipelineService(db).update(pipeline_id, data)


@router.post("/{pipeline_id}/stages", response_model=StageRead, status_code=status.HTTP_201_CREATED)
def add_stage(pipeline_id: UUID, data: StageCreate, _: User = Depends(gestor),
              db: Session = Depends(get_db)):
    return PipelineService(db).add_stage(pipeline_id, data)


@router.put("/{pipeline_id}/stages/{stage_id}", response_model=StageRead)
def update_stage(pipeline_id: UUID, stage_id: UUID, data: StageCreate, _: User = Depends(gestor),
                 db: Session = Depends(get_db)):
    return PipelineService(db).update_stage(pipeline_id, stage_id, data)


@router.delete("/{pipeline_id}/stages/{stage_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_stage(pipeline_id: UUID, stage_id: UUID, _: User = Depends(gestor),
                 db: Session = Depends(get_db)):
    PipelineService(db).delete_stage(pipeline_id, stage_id)
    return None


@router.get("/{pipeline_id}/board", response_model=BoardResponse)
def get_board(pipeline_id: UUID, _: User = Depends(get_current_user),
              db: Session = Depends(get_db)):
    return PipelineService(db).board(pipeline_id)
