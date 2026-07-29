"""Rotas do tenant atual."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models.user import User, UserRole
from app.schemas.lead_prospect import IcpScoringRules
from app.schemas.tenant import TenantRead, TenantUpdate
from app.services.lead_prospect import LeadProspectService
from app.services.tenant import TenantService

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
