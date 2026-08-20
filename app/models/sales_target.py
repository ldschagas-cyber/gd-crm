"""SalesTarget — meta de venda de um vendedor num mês (quantidade e valor).

Uma linha por (tenant, vendedor, mês) — a meta muda mês a mês. A meta da equipe
não é gravada: é derivada somando as metas dos vendedores da equipe no mês. O
realizado também não é gravado — é lido ao vivo dos negócios ganhos (Deal
status=ganho, data_fechamento no mês), no mesmo espírito das Metas do Funil. Ver
docs/PLANO_METAS_VENDA.md e MetasVendaService.
"""
import uuid

from sqlalchemy import ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin, uuid_pk


class SalesTarget(Base, TenantMixin, TimestampMixin):
    __tablename__ = "sales_targets"
    __table_args__ = (
        UniqueConstraint("tenant_id", "user_id", "mes", name="uq_sales_target_tenant_user_mes"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    mes: Mapped[str] = mapped_column(String(7), nullable=False)  # "AAAA-MM"
    meta_qtd: Mapped[int | None] = mapped_column(Integer)
    meta_valor: Mapped[float | None] = mapped_column(Numeric(15, 2))
