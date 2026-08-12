"""Rotas de usuários (restritas ao admin)."""
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models.user import User, UserRole
from app.schemas.common import Page, PageParams
from app.schemas.user import UserCreate, UserRead, UserResetLinkOut, UserStatusUpdate, UserUpdate
from app.services.user import UserService
from sqlalchemy.orm import Session

router = APIRouter(prefix="/users", tags=["Usuários"])
admin_only = require_roles(UserRole.ADMIN.value)


@router.get("", response_model=Page[UserRead])
def list_users(params: PageParams = Depends(), busca: str | None = None, perfil: str | None = None,
               _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Qualquer usuário autenticado do tenant pode listar (usado para popular
    # seletores de "atribuir a"/"pesquisado por" em várias telas — Pesquisa de
    # Leads, Negócios, Tarefas, etc.). Só create/update/status seguem admin-only.
    items, total = UserService(db).list(params, busca, perfil)
    return Page(items=items, total=total, page=params.page, size=params.size)


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(data: UserCreate, _: User = Depends(admin_only), db: Session = Depends(get_db)):
    return UserService(db).create(data)


@router.get("/{user_id}", response_model=UserRead)
def get_user(user_id: UUID, _: User = Depends(admin_only), db: Session = Depends(get_db)):
    return UserService(db).get(user_id)


@router.put("/{user_id}", response_model=UserRead)
def update_user(user_id: UUID, data: UserUpdate, _: User = Depends(admin_only),
                db: Session = Depends(get_db)):
    return UserService(db).update(user_id, data)


@router.patch("/{user_id}/status", response_model=UserRead)
def set_status(user_id: UUID, data: UserStatusUpdate, _: User = Depends(admin_only),
               db: Session = Depends(get_db)):
    return UserService(db).set_status(user_id, data)


@router.post("/{user_id}/reset-link", response_model=UserResetLinkOut)
def generate_reset_link(user_id: UUID, _: User = Depends(admin_only), db: Session = Depends(get_db)):
    link, expira_em_minutos = UserService(db).generate_reset_link(user_id)
    return UserResetLinkOut(link=link, expira_em_minutos=expira_em_minutos)
