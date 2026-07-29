"""Repository base com isolamento multi-tenant automático.

Toda leitura e escrita são filtradas/atribuídas pelo tenant atual obtido do
contexto de requisição (definido a partir do JWT). Nenhuma query escapa do
tenant corrente.
"""
from typing import Generic, TypeVar
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.context import get_current_tenant
from app.models.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    model: type[ModelT]

    def __init__(self, db: Session):
        self.db = db

    # ---- helpers internos -------------------------------------------------
    def _tenant_id(self) -> UUID:
        tenant_id = get_current_tenant()
        if tenant_id is None:
            raise RuntimeError("Tenant não definido no contexto da requisição")
        return tenant_id

    def _base_query(self):
        return select(self.model).where(self.model.tenant_id == self._tenant_id())

    # ---- operações genéricas ---------------------------------------------
    def get(self, id_: UUID) -> ModelT | None:
        stmt = self._base_query().where(self.model.id == id_)
        return self.db.execute(stmt).scalar_one_or_none()

    def list(self, *filters, offset: int = 0, limit: int = 20, order_by=None) -> tuple[list[ModelT], int]:
        stmt = self._base_query()
        for f in filters:
            stmt = stmt.where(f)
        total = self.db.execute(
            select(func.count()).select_from(stmt.subquery())
        ).scalar_one()
        if order_by is not None:
            stmt = stmt.order_by(order_by)
        stmt = stmt.offset(offset).limit(limit)
        items = list(self.db.execute(stmt).scalars().all())
        return items, total

    def add(self, obj: ModelT) -> ModelT:
        # Garante o tenant_id a partir do contexto, ignorando qualquer valor externo.
        obj.tenant_id = self._tenant_id()
        self.db.add(obj)
        self.db.flush()
        self.db.refresh(obj)
        return obj

    def save(self, obj: ModelT) -> ModelT:
        self.db.flush()
        self.db.refresh(obj)
        return obj

    def delete(self, obj: ModelT) -> None:
        self.db.delete(obj)
        self.db.flush()
