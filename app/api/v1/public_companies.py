"""Rotas de Buscar Empresas (proxy de busca pública de CNPJ + bulk-add p/ Pesquisa de Leads)."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.public_company import (
    PublicCompanyBulkAddRequest, PublicCompanyBulkAddResponse, PublicCompanySearchResponse,
)
from app.services.public_company_search import PublicCompanyService, PublicCompanySearchService

router = APIRouter(prefix="/public-companies", tags=["Buscar Empresas"])


@router.get("/search", response_model=PublicCompanySearchResponse)
def search_public_companies(
    cnae: list[str] = Query(...),
    regiao: list[str] | None = Query(None),
    uf: list[str] | None = Query(None),
    porte: str | None = Query(None),
    cursor: str | None = Query(None),
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return PublicCompanySearchService(db).search(cnae=cnae, regiao=regiao, uf=uf, porte=porte, cursor=cursor)


@router.post("/bulk-add", response_model=PublicCompanyBulkAddResponse)
def bulk_add_public_companies(
    data: PublicCompanyBulkAddRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return PublicCompanyService(db).bulk_add(data.empresas, pesquisado_por=user.id)
