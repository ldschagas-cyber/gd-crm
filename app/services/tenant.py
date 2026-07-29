"""Serviço de tenant."""
from sqlalchemy.orm import Session

from app.core.context import get_current_tenant
from app.core.exceptions import NotFoundError
from app.models.tenant import Tenant
from app.schemas.tenant import TenantUpdate


class TenantService:
    def __init__(self, db: Session):
        self.db = db

    def get_current(self) -> Tenant:
        tenant = self.db.get(Tenant, get_current_tenant())
        if tenant is None:
            raise NotFoundError("Tenant não encontrado")
        return tenant

    def update(self, data: TenantUpdate) -> Tenant:
        tenant = self.get_current()
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(tenant, field, value)
        self.db.flush()
        self.db.refresh(tenant)
        return tenant
