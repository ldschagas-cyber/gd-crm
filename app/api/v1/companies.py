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
    CentralLeadRead, CentralLeadsResumo, CompanyAskRequest, CompanyAskResponse, CompanyCreate, CompanyCsFaseUpdate,
    CompanyCsUpdate, CompanyDossierUpdate, CompanyFilterOptions, CompanyFunilEstagioUpdate, CompanyIcpRead,
    CompanyRead, CompanyStatusUpdate, CompanyUpdate, CsCheckinCreate, HealthScoreRead,
)
from app.schemas.import_job import ImportJobRead
from app.schemas.onboarding import OnboardingItemRead, OnboardingItemStatusUpdate
from app.schemas.timeline import TimelineEventRead, TimelineNoteCreate
from app.services.company import CompanyService
from app.services.company_ai import CompanyAiService
from app.services.import_job import ImportJobService
from app.services.onboarding import OnboardingService
from app.services.sdr_argos import SdrArgosService
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


@router.post("/import-empresas-contatos", response_model=ImportJobRead, status_code=status.HTTP_202_ACCEPTED)
def import_companies_contacts(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Importação combinada: cada linha cria (ou reaproveita, se já cadastrada pro mesmo
    responsável) a empresa e o contato juntos — ver ImportType.EMPRESAS_CONTATOS e
    app/workers/tasks.import_companies_contacts_task."""
    if not file.filename or not file.filename.lower().endswith((".csv", ".xlsx")):
        raise HTTPException(status_code=422, detail="Envie um arquivo .csv ou .xlsx")
    content = file.file.read()
    job = ImportJobService(db).create_and_dispatch(
        tipo=ImportType.EMPRESAS_CONTATOS.value, filename=file.filename, content=content,
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


# ---- Central de Leads --------------------------------------------------------
# Rotas estáticas antes de /{company_id} — senão "central-leads" seria interpretado
# como um UUID de empresa e cairia (422) na rota dinâmica abaixo.

@router.get("/central-leads", response_model=list[CentralLeadRead])
def list_central_leads(
    funil_estagio: str | None = None,
    responsavel_id: UUID | None = None,
    busca: str | None = None,
    lead_score_min: int | None = None,
    em_cadencia: bool | None = None,
    esconder_convertidos_apos_dias: int | None = None,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return CompanyService(db).list_central_leads(
        funil_estagio=funil_estagio, responsavel_id=responsavel_id, busca=busca,
        lead_score_min=lead_score_min, em_cadencia=em_cadencia,
        esconder_convertidos_apos_dias=esconder_convertidos_apos_dias,
    )


@router.get("/central-leads/resumo", response_model=CentralLeadsResumo)
def get_central_leads_resumo(_: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return CompanyService(db).resumo_central_leads()


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


@router.patch("/{company_id}/funil-estagio", response_model=CompanyRead)
def set_funil_estagio(company_id: UUID, data: CompanyFunilEstagioUpdate, _: User = Depends(get_current_user),
                      db: Session = Depends(get_db)):
    """Única porta pra MQL/SQL: essas transições nunca têm gatilho automático no
    backend, só chegam aqui por uma ação explícita do usuário na Central de Leads."""
    return CompanyService(db).set_funil_estagio(company_id, data)


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


@router.post("/{company_id}/sdr-argos", response_model=CompanyRead, status_code=status.HTTP_200_OK)
def run_sdr_argos(company_id: UUID, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Gatilho manual ("botão SDR Argos") — a regra padrão é automática em background no
    handoff da promoção (LeadProspectService.promote), isso aqui é pra re-rodar sob demanda
    (ex.: depois de editar o setor da empresa). Nunca dispara contato externo — só gera
    dossiê/argumento/roteiro e sugere a cadência (ver app/services/sdr_argos.py)."""
    SdrArgosService(db).gerar(company_id)
    return CompanyService(db).get(company_id)


# ---- Customer Success ---------------------------------------------------------
# Ver docs/PLANO_CUSTOMER_SUCCESS.md. Listagem/resumo agregados do módulo de Clientes
# ficam em app/api/v1/customer_success.py (prefixo /clientes) — aqui só os
# sub-recursos por empresa, mesmo padrão de /timeline, /icp, /dossie acima.

@router.patch("/{company_id}/cs", response_model=CompanyRead)
def set_company_cs(company_id: UUID, data: CompanyCsUpdate, _: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    return CompanyService(db).set_cs(company_id, data)


@router.patch("/{company_id}/cs-fase", response_model=CompanyRead)
def set_company_cs_fase(company_id: UUID, data: CompanyCsFaseUpdate, _: User = Depends(get_current_user),
                        db: Session = Depends(get_db)):
    """Troca manual de fase (drag no kanban / seletor no drawer). `churn` nunca chega
    aqui — só via cancelamento de Assinatura, ver PATCH /assinaturas/{id}/cancelar."""
    return CompanyService(db).set_cs_fase(company_id, data)


@router.get("/{company_id}/health", response_model=HealthScoreRead)
def get_company_health(company_id: UUID, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return CompanyService(db).get_health(company_id)


@router.post("/{company_id}/checkins", response_model=HealthScoreRead, status_code=status.HTTP_201_CREATED)
def create_checkin(company_id: UUID, data: CsCheckinCreate, _: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    return CompanyService(db).register_checkin(company_id, data)


@router.get("/{company_id}/onboarding", response_model=list[OnboardingItemRead])
def list_onboarding(company_id: UUID, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    CompanyService(db).get(company_id)  # valida existência/tenant
    return OnboardingService(db).list_by_company(company_id)


@router.patch("/{company_id}/onboarding/{item_id}", response_model=OnboardingItemRead)
def set_onboarding_item_status(company_id: UUID, item_id: UUID, data: OnboardingItemStatusUpdate,
                               _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return OnboardingService(db).set_item_status(company_id, item_id, data)
