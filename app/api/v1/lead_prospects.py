"""Rotas de pesquisa de leads (item 9.1 — pré-CRM)."""
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models.import_job import ImportType
from app.models.user import User, UserRole
from app.schemas.common import Page
from app.schemas.import_job import ImportJobRead
from app.schemas.lead_prospect import (
    CommercialIntelligenceResponse, LeadEnrichmentSuggestion, LeadPromoteRequest, LeadProspectCreate,
    LeadProspectPageParams, LeadProspectRead, LeadProspectUpdate, MetaProgressResponse, PerformanceReportResponse,
)
from app.services.commercial_intelligence import CommercialIntelligenceService
from app.services.import_job import ImportJobService
from app.services.lead_enrichment import LeadEnrichmentService
from app.services.lead_prospect import LeadProspectService

router = APIRouter(prefix="/lead-prospects", tags=["Pesquisa de Leads"])


@router.get("", response_model=Page[LeadProspectRead])
def list_leads(
    params: LeadProspectPageParams = Depends(),
    status_: str | None = Query(None, alias="status"),
    icp_fit: str | None = None,
    pesquisado_por: UUID | None = None,
    busca: str | None = None,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items, total = LeadProspectService(db).list(
        params, status=status_, pesquisado_por=pesquisado_por, busca=busca, icp_fit=icp_fit,
    )
    return Page(items=items, total=total, page=params.page, size=params.size)


@router.post("", response_model=LeadProspectRead, status_code=status.HTTP_201_CREATED)
def create_lead(data: LeadProspectCreate, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return LeadProspectService(db).create(data)


@router.post("/import", response_model=ImportJobRead, status_code=status.HTTP_202_ACCEPTED)
def import_leads(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not file.filename or not file.filename.lower().endswith((".csv", ".xlsx")):
        raise HTTPException(status_code=422, detail="Envie um arquivo .csv ou .xlsx")
    content = file.file.read()
    job = ImportJobService(db).create_and_dispatch(
        tipo=ImportType.LEAD_PROSPECTS.value, filename=file.filename, content=content,
        tenant_id=user.tenant_id, user_id=user.id,
    )
    return job


@router.get("/import/{job_id}", response_model=ImportJobRead)
def get_import_job(job_id: UUID, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    job = ImportJobService(db).get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job de importação não encontrado")
    return job


@router.get("/performance-report", response_model=PerformanceReportResponse)
def performance_report(
    mes: str = Query(..., pattern=r"^\d{4}-\d{2}$"),
    _: User = Depends(require_roles(UserRole.ADMIN.value, UserRole.GESTOR.value)),
    db: Session = Depends(get_db),
):
    return LeadProspectService(db).performance_report(mes)


@router.get("/metas", response_model=MetaProgressResponse)
def metas_progress(
    _: User = Depends(require_roles(UserRole.ADMIN.value, UserRole.GESTOR.value)),
    db: Session = Depends(get_db),
):
    return LeadProspectService(db).metas_progress()


@router.get("/{lead_id}", response_model=LeadProspectRead)
def get_lead(lead_id: UUID, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return LeadProspectService(db).get(lead_id)


@router.put("/{lead_id}", response_model=LeadProspectRead)
def update_lead(lead_id: UUID, data: LeadProspectUpdate, _: User = Depends(get_current_user),
               db: Session = Depends(get_db)):
    return LeadProspectService(db).update(lead_id, data)


@router.delete("/{lead_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lead(lead_id: UUID, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    LeadProspectService(db).delete(lead_id)
    return None


@router.post("/{lead_id}/promote", response_model=LeadProspectRead)
def promote_lead(
    lead_id: UUID, data: LeadPromoteRequest,
    _: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    return LeadProspectService(db).promote(lead_id, data.responsavel_id)


@router.post("/{lead_id}/enrich", response_model=LeadEnrichmentSuggestion)
def enrich_lead(lead_id: UUID, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Só sugere — não grava nada. O frontend mostra as sugestões e o usuário
    decide se aceita (via PUT normal em /lead-prospects/{id})."""
    lead = LeadProspectService(db).get_orm(lead_id)
    return LeadEnrichmentService().enrich(lead)


@router.post("/{lead_id}/inteligencia-comercial", response_model=CommercialIntelligenceResponse)
def gerar_inteligencia_comercial(lead_id: UUID, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Cruza o perfil pesquisado do lead com o Benchmark Logístico do Diagnóstico
    para montar um argumento comercial. Só sugere — nada é gravado."""
    lead = LeadProspectService(db).get_orm(lead_id)
    return CommercialIntelligenceService().gerar(lead)


@router.patch("/{lead_id}/inteligencia-comercial", response_model=LeadProspectRead)
def gravar_inteligencia_comercial(
    lead_id: UUID, data: CommercialIntelligenceResponse,
    _: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    """Grava no lead um resultado já obtido via POST .../inteligencia-comercial (o
    usuário decide se vale gravar depois de revisar). É copiado para a Company
    correspondente quando (e se) o lead for promovido — ver LeadProspectService.promote()."""
    return LeadProspectService(db).save_inteligencia_comercial(lead_id, data)
