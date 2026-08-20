"""Rotas de Metas do Funil — controle de mudança de fase por percentual (Anexo 1).
Ver docs/PLANO_METAS_FUNIL.md."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_roles
from app.models.user import User, UserRole
from app.schemas.funil_metas import FunilMetasResumo
from app.services.funil_metas import FunilMetasService

router = APIRouter(prefix="/funil-metas", tags=["Metas do Funil"])
gestor = require_roles(UserRole.ADMIN.value, UserRole.GESTOR.value)


@router.get("/resumo", response_model=FunilMetasResumo)
def get_resumo(
    mes: str | None = Query(None, pattern=r"^\d{4}-\d{2}$"),
    ano: str | None = Query(None, pattern=r"^\d{4}$"),
    modo: str = Query("atividade", pattern="^(atividade|coorte)$"),
    _: User = Depends(gestor),
    db: Session = Depends(get_db),
):
    """Visão mensal (mes=AAAA-MM) ou anual agregada (ano=AAAA) — informe exatamente um."""
    return FunilMetasService(db).resumo(modo, mes=mes, ano=ano)
