"""Rotas de negócios."""
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.common import Page, PageParams
from app.schemas.deal import (
    DealClose, DealCreate, DealRead, DealStageMove, DealUpdate,
)
from app.schemas.timeline import TimelineEventRead, TimelineNoteCreate
from app.repositories.timeline import TimelineRepository
from app.services.deal import DealService
from app.services.timeline import TimelineService

router = APIRouter(prefix="/deals", tags=["Negócios"])


@router.get("", response_model=Page[DealRead])
def list_deals(
    params: PageParams = Depends(),
    pipeline_id: UUID | None = None,
    stage_id: UUID | None = None,
    status_: str | None = Query(None, alias="status"),
    responsavel_id: UUID | None = None,
    company_id: UUID | None = None,
    busca: str | None = None,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items, total = DealService(db).list(params, pipeline_id, stage_id, status_, responsavel_id, company_id, busca)
    return Page(items=items, total=total, page=params.page, size=params.size)


@router.post("", response_model=DealRead, status_code=status.HTTP_201_CREATED)
def create_deal(data: DealCreate, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return DealService(db).create(data)


@router.get("/{deal_id}", response_model=DealRead)
def get_deal(deal_id: UUID, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return DealService(db).get(deal_id)


@router.put("/{deal_id}", response_model=DealRead)
def update_deal(deal_id: UUID, data: DealUpdate, _: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    return DealService(db).update(deal_id, data)


@router.patch("/{deal_id}/stage", response_model=DealRead)
def move_stage(deal_id: UUID, data: DealStageMove, _: User = Depends(get_current_user),
               db: Session = Depends(get_db)):
    return DealService(db).move_stage(deal_id, data)


@router.patch("/{deal_id}/close", response_model=DealRead)
def close_deal(deal_id: UUID, data: DealClose, _: User = Depends(get_current_user),
               db: Session = Depends(get_db)):
    return DealService(db).close(deal_id, data)


@router.get("/{deal_id}/timeline", response_model=Page[TimelineEventRead])
def get_deal_timeline(deal_id: UUID, params: PageParams = Depends(),
                      _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    DealService(db).get(deal_id)  # valida existência/tenant
    items, total = TimelineRepository(db).list_by_deal(deal_id, params.offset, params.size)
    return Page(items=items, total=total, page=params.page, size=params.size)


@router.post("/{deal_id}/timeline", response_model=TimelineEventRead, status_code=status.HTTP_201_CREATED)
def add_deal_note(deal_id: UUID, data: TimelineNoteCreate, _: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    deal = DealService(db).get(deal_id)
    return TimelineService(db).registrar_from_schema(deal.company_id, data, deal_id=deal.id)
