"""Rotas dos dashboards."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models.user import User, UserRole
from app.schemas.dashboard import CommercialDashboard, SellerDashboard
from app.services.dashboard import DashboardService

router = APIRouter(prefix="/dashboards", tags=["Dashboards"])


@router.get("/commercial", response_model=CommercialDashboard)
def commercial(
    _: User = Depends(require_roles(UserRole.ADMIN.value, UserRole.GESTOR.value)),
    db: Session = Depends(get_db),
):
    return DashboardService(db).commercial()


@router.get("/seller", response_model=SellerDashboard)
def seller(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return DashboardService(db).seller(user.id)
