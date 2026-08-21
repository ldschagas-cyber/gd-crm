"""CallTarget — meta de ligações de um vendedor num mês (semanal e mensal).

Uma linha por (tenant, vendedor, mês) — a meta muda mês a mês, no mesmo modelo do
SalesTarget. O realizado não é gravado: é lido ao vivo das tarefas tipo=ligacao
concluídas. Ver docs/PLANO_METAS_VENDA.md e MetasLigacoesService.
"""
import uuid

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin, uuid_pk


class CallTarget(Base, TenantMixin, TimestampMixin):
    __tablename__ = "call_targets"
    __table_args__ = (
        UniqueConstraint("tenant_id", "user_id", "mes", name="uq_call_target_tenant_user_mes"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    mes: Mapped[str] = mapped_column(String(7), nullable=False)  # "AAAA-MM"
    meta_semanal: Mapped[int | None] = mapped_column(Integer)
    meta_mensal: Mapped[int | None] = mapped_column(Integer)
