"""Rotas do tenant atual."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models.user import User, UserRole
from app.schemas.company import LeadScoreRules
from app.schemas.funil_metas import FunilMetasConfig
from app.schemas.lead_prospect import IcpScoringRules
from app.schemas.tenant import TenantRead, TenantUpdate
from app.services.company import CompanyService
from app.services.funil_metas import FunilMetasService
from app.services.lead_prospect import LeadProspectService
from app.services.tenant import TenantService
from app.services import twilio_whatsapp

router = APIRouter(prefix="/tenant", tags=["Tenant"])


@router.get("", response_model=TenantRead)
def get_tenant(_: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return TenantService(db).get_current()


@router.put("", response_model=TenantRead)
def update_tenant(
    data: TenantUpdate,
    _: User = Depends(require_roles(UserRole.ADMIN.value)),
    db: Session = Depends(get_db),
):
    return TenantService(db).update(data)


@router.get("/icp-scoring-rules")
def get_icp_scoring_rules(_: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return LeadProspectService(db).get_rules()


@router.put("/icp-scoring-rules")
def update_icp_scoring_rules(
    data: IcpScoringRules,
    _: User = Depends(require_roles(UserRole.ADMIN.value)),
    db: Session = Depends(get_db),
):
    return LeadProspectService(db).update_rules(data)


@router.get("/lead-score-rules")
def get_lead_score_rules(_: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Pesos do componente de Engajamento do Lead Score (Central de Leads) — o
    componente de Fit ICP continua sendo /icp-scoring-rules, acima."""
    return CompanyService(db).get_lead_score_rules()


@router.put("/lead-score-rules")
def update_lead_score_rules(
    data: LeadScoreRules,
    _: User = Depends(require_roles(UserRole.ADMIN.value)),
    db: Session = Depends(get_db),
):
    return CompanyService(db).update_lead_score_rules(data)


@router.get("/whatsapp-status")
def get_whatsapp_status(_: User = Depends(get_current_user)):
    """Envio automático de WhatsApp em Sequências (app/services/twilio_whatsapp.py)
    é config de servidor, não por usuário — não tem nada pra "conectar" aqui, só
    reflete se TWILIO_WHATSAPP_FROM (e o resto das credenciais Twilio) já foi
    configurado, pra Preferências mostrar o status certo (WhatsappTab)."""
    return {"configurado": twilio_whatsapp.is_configured()}


@router.get("/funil-metas")
def get_funil_metas(_: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Config do controle de fase por percentual (Anexo 1) — meta de empresas
    pesquisadas e % esperado de cada etapa em relação à anterior. Ver
    docs/PLANO_METAS_FUNIL.md."""
    return FunilMetasService(db).get_config()


@router.put("/funil-metas")
def update_funil_metas(
    data: FunilMetasConfig,
    _: User = Depends(require_roles(UserRole.ADMIN.value, UserRole.GESTOR.value)),
    db: Session = Depends(get_db),
):
    return FunilMetasService(db).update_config(data)
