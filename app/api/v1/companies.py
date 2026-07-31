"""Rotas de empresas, incluindo timeline, importação e exportação."""
import csv
import io
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.import_job import ImportType
from app.models.user import User
from app.schemas.common import Page, PageParams
from app.schemas.company import (
    CompanyAskRequest, CompanyAskResponse, CompanyCreate, CompanyDossierUpdate, CompanyFilterOptions,
    CompanyIcpRead, CompanyRead, CompanyStatusUpdate, CompanyUpdate,
)
from app.schemas.import_job import ImportJobRead
from app.schemas.timeline import TimelineEventRead, TimelineNoteCreate
from app.services.company import CompanyService
from app.services.company_ai import CompanyAiService
from app.services.import_job import ImportJobService
from app.services.timeline import TimelineService
from app.repositories.timeline import TimelineRepository

router = APIRouter(prefix="/companies", tags=["Empresas"])

EXPORT_COLUMNS = [
    "razao_social", "cnpj", "cidade", "uf", "segmento", "telefone",
    "email", "porte", "num_funcionarios", "faturamento_estimado",
    "origem", "status",
]


@router.get("", response_model=Page[CompanyRead])
def list_companies(
    params: PageParams = Depends(),
    status_: str | None = Query(None, alias="status"),
    uf: str | None = None,
    busca: str | None = None,
    responsavel_id: UUID | None = None,
    segmento: str | None = None,
    porte: str | None = None,
    origem: str | None = None,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items, total = CompanyService(db).list(
        params, status=status_, uf=uf, busca=busca, responsavel_id=responsavel_id,
        segmento=segmento, porte=porte, origem=origem,
    )
    return Page(items=items, total=total, page=params.page, size=params.size)


@router.post("", response_model=CompanyRead, status_code=status.HTTP_201_CREATED)
def create_company(data: CompanyCreate, _: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    return CompanyService(db).create(data)


@router.get("/export")
def export_companies(
    status_: str | None = Query(None, alias="status"),
    uf: str | None = None,
    busca: str | None = None,
    responsavel_id: UUID | None = None,
    segmento: str | None = None,
    porte: str | None = None,
    origem: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items = CompanyService(db).list_for_export(
        status=status_, uf=uf, busca=busca, responsavel_id=responsavel_id,
        segmento=segmento, porte=porte, origem=origem,
    )
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(EXPORT_COLUMNS)
    for c in items:
        writer.writerow([getattr(c, col) or "" for col in EXPORT_COLUMNS])
    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=empresas.csv"},
    )


@router.post("/import", response_model=ImportJobRead, status_code=status.HTTP_202_ACCEPTED)
def import_companies(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not file.filename or not file.filename.lower().endswith((".csv", ".xlsx")):
        raise HTTPException(status_code=422, detail="Envie um arquivo .csv ou .xlsx")
    content = file.file.read()
    job = ImportJobService(db).create_and_dispatch(
        tipo=ImportType.EMPRESAS.value, filename=file.filename, content=content,
        tenant_id=user.tenant_id, user_id=user.id,
    )
    return job


@router.get("/import/{job_id}", response_model=ImportJobRead)
def get_import_job(job_id: UUID, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    job = ImportJobService(db).get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job de importação não encontrado")
    return job


@router.get("/filter-options", response_model=CompanyFilterOptions)
def filter_options(_: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return CompanyService(db).filter_options()


@router.get("/{company_id}", response_model=CompanyRead)
def get_company(company_id: UUID, _: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    return CompanyService(db).get(company_id)


@router.put("/{company_id}", response_model=CompanyRead)
def update_company(company_id: UUID, data: CompanyUpdate, _: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    return CompanyService(db).update(company_id, data)


@router.patch("/{company_id}/status", response_model=CompanyRead)
def set_status(company_id: UUID, data: CompanyStatusUpdate, _: User = Depends(get_current_user),
               db: Session = Depends(get_db)):
    return CompanyService(db).set_status(company_id, data)


@router.delete("/{company_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_company(company_id: UUID, _: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    CompanyService(db).soft_delete(company_id)
    return None


@router.get("/{company_id}/timeline", response_model=Page[TimelineEventRead])
def get_timeline(company_id: UUID, params: PageParams = Depends(),
                 _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    CompanyService(db).get(company_id)  # valida existência/tenant
    items, total = TimelineRepository(db).list_by_company(company_id, params.offset, params.size)
    return Page(items=items, total=total, page=params.page, size=params.size)


@router.post("/{company_id}/timeline", response_model=TimelineEventRead,
             status_code=status.HTTP_201_CREATED)
def add_note(company_id: UUID, data: TimelineNoteCreate, _: User = Depends(get_current_user),
             db: Session = Depends(get_db)):
    CompanyService(db).get(company_id)
    return TimelineService(db).registrar_from_schema(company_id, data)


# ---- Dossiê Comercial -------------------------------------------------------

@router.get("/{company_id}/icp", response_model=CompanyIcpRead)
def get_company_icp(company_id: UUID, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return CompanyService(db).get_icp(company_id)


@router.put("/{company_id}/dossie", response_model=CompanyRead)
def update_company_dossier(company_id: UUID, data: CompanyDossierUpdate,
                           _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return CompanyService(db).update_dossier(company_id, data)


@router.post("/{company_id}/dossie/resumo/atualizar", response_model=CompanyRead,
             status_code=status.HTTP_200_OK)
def regenerate_company_resumo(company_id: UUID, _: User = Depends(get_current_user),
                              db: Session = Depends(get_db)):
    """Gatilho manual ("Atualizar agora") — a regra padrão é automática em background
    a cada evento relevante da timeline, isso aqui é só uma rede de segurança síncrona."""
    CompanyAiService(db).regenerate_resumo(company_id)
    return CompanyService(db).get(company_id)


@router.post("/{company_id}/dossie/perguntar", response_model=CompanyAskResponse)
def ask_company_ai(company_id: UUID, data: CompanyAskRequest, _: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    return CompanyAiService(db).perguntar(company_id, data.pergunta)
