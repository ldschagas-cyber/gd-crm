"""Rotas de equipes de vendas. Listagem aberta a qualquer usuário autenticado (pra
popular seletores); criação/edição/remoção restritas ao admin."""
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models.user import User, UserRole
from app.schemas.team import TeamCreate, TeamRead, TeamUpdate
from app.services.team import TeamService

router = APIRouter(prefix="/teams", tags=["Equipes"])
admin_only = require_roles(UserRole.ADMIN.value)


@router.get("", response_model=list[TeamRead])
def list_teams(_: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return TeamService(db).list()


@router.post("", response_model=TeamRead, status_code=status.HTTP_201_CREATED)
def create_team(data: TeamCreate, _: User = Depends(admin_only), db: Session = Depends(get_db)):
    return TeamService(db).create(data)


@router.put("/{team_id}", response_model=TeamRead)
def update_team(team_id: UUID, data: TeamUpdate, _: User = Depends(admin_only), db: Session = Depends(get_db)):
    return TeamService(db).update(team_id, data)


@router.delete("/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_team(team_id: UUID, _: User = Depends(admin_only), db: Session = Depends(get_db)):
    TeamService(db).delete(team_id)
