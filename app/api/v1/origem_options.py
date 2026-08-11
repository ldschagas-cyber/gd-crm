"""Rotas de opções de Origem (cadastro incremental via formulário de Empresa/Pesquisa de Leads)."""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.origem_option import OrigemOptionCreate, OrigemOptionRead
from app.services.origem_option import OrigemOptionService

router = APIRouter(prefix="/origem-options", tags=["Opções de Origem"])


@router.get("", response_model=list[str])
def list_origem_options(_: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return OrigemOptionService(db).list()


@router.post("", response_model=OrigemOptionRead, status_code=status.HTTP_201_CREATED)
def create_origem_option(data: OrigemOptionCreate, _: User = Depends(get_current_user),
                         db: Session = Depends(get_db)):
    return OrigemOptionService(db).create(data)
