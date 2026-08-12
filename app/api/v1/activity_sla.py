"""Rotas de SLA Comercial: CRUD de regras + painel de cumprimento (ver
docs/PLANO_SLA_COMERCIAL.md). Regras são configuração (mesmo nível de sensibilidade de
Pipelines) — só admin/gestor mexem; o resumo é lido por qualquer usuário autenticado, igual
ao Dashboard."""
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models.user import User, UserRole
from app.schemas.activity_sla_rule import ActivitySlaRuleCreate, ActivitySlaRuleRead, ActivitySlaRuleUpdate, SlaResumoResponse
from app.services.activity_sla import ActivitySlaService

router = APIRouter(prefix="/activity-sla", tags=["SLA Comercial"])
gestor = require_roles(UserRole.ADMIN.value, UserRole.GESTOR.value)


@router.get("/rules", response_model=list[ActivitySlaRuleRead])
def list_rules(_: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ActivitySlaService(db).list_rules()


@router.post("/rules", response_model=ActivitySlaRuleRead, status_code=status.HTTP_201_CREATED)
def create_rule(data: ActivitySlaRuleCreate, _: User = Depends(gestor), db: Session = Depends(get_db)):
    return ActivitySlaService(db).create_rule(data)


@router.put("/rules/{rule_id}", response_model=ActivitySlaRuleRead)
def update_rule(rule_id: UUID, data: ActivitySlaRuleUpdate, _: User = Depends(gestor),
                db: Session = Depends(get_db)):
    return ActivitySlaService(db).update_rule(rule_id, data)


@router.delete("/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rule(rule_id: UUID, _: User = Depends(gestor), db: Session = Depends(get_db)):
    ActivitySlaService(db).delete_rule(rule_id)
    return None


@router.get("/resumo", response_model=SlaResumoResponse)
def get_resumo(_: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ActivitySlaService(db).resumo()
