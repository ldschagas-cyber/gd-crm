"""Rotas do módulo de Clientes (Customer Success) — listagem e resumo agregado.
Sub-recursos por empresa (cs-fase, health, onboarding, check-ins) ficam em
app/api/v1/companies.py. Ver docs/PLANO_CUSTOMER_SUCCESS.md."""
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.company import ClienteRead, ClientesResumo
from app.services.company import CompanyService

router = APIRouter(prefix="/clientes", tags=["Customer Success"])


@router.get("", response_model=list[ClienteRead])
def list_clientes(
    cs_fase: str | None = None,
    cs_responsavel_id: UUID | None = None,
    busca: str | None = None,
    health_score_max: int | None = None,
    renovacao_ate_dias: int | None = None,
    somente_em_risco: bool = False,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return CompanyService(db).list_clientes(
        cs_fase=cs_fase, cs_responsavel_id=cs_responsavel_id, busca=busca,
        health_score_max=health_score_max, renovacao_ate_dias=renovacao_ate_dias,
        somente_em_risco=somente_em_risco,
    )


@router.get("/resumo", response_model=ClientesResumo)
def get_clientes_resumo(_: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return CompanyService(db).resumo_clientes()
