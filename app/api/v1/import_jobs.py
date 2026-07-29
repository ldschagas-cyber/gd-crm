"""Rota central de histórico de importações (empresas/contatos), usada em Configurações."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.common import Page, PageParams
from app.schemas.import_job import ImportJobRead
from app.services.import_job import ImportJobService

router = APIRouter(prefix="/import-jobs", tags=["Importações"])


@router.get("", response_model=Page[ImportJobRead])
def list_import_jobs(params: PageParams = Depends(), _: User = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    items, total = ImportJobService(db).list_recent(params.offset, params.size)
    return Page(items=items, total=total, page=params.page, size=params.size)
