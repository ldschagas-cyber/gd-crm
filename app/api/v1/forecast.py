"""Rotas de Previsão Comercial (Forecast/Commit)."""
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.forecast import ForecastResumo
from app.services.forecast import ForecastService

router = APIRouter(prefix="/forecast", tags=["Previsão Comercial"])


@router.get("/resumo", response_model=ForecastResumo)
def resumo(
    mes: str = Query(..., description="Mês no formato AAAA-MM"),
    pipeline_id: UUID | None = None,
    responsavel_id: UUID | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Sem require_roles: qualquer usuário autenticado pode consultar — o serviço
    # restringe o recorte ao próprio responsavel_id quando o perfil não é gestão.
    return ForecastService(db).resumo(mes, user, pipeline_id, responsavel_id)
