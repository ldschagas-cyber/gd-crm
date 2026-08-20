"""Rotas de Metas de Ligações — progresso por vendedor (semana/mês correntes).
Restritas a admin e gestor (mesmo critério das Metas de Pesquisa)."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_roles
from app.models.user import User, UserRole
from app.schemas.metas_ligacoes import MetaLigacoesResponse
from app.services.metas_ligacoes import MetasLigacoesService

router = APIRouter(prefix="/metas-ligacoes", tags=["Metas de Ligações"])
gestor = require_roles(UserRole.ADMIN.value, UserRole.GESTOR.value)


@router.get("/progresso", response_model=MetaLigacoesResponse)
def get_progresso(_: User = Depends(gestor), db: Session = Depends(get_db)):
    return MetasLigacoesService(db).progresso()
