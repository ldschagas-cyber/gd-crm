"""Workflow / WorkflowAction / WorkflowExecutionLog — motor evento→condição→ação (RF018, §7.9)."""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantMixin, TimestampMixin, uuid_pk


class Workflow(Base, TenantMixin, TimestampMixin):
    __tablename__ = "workflows"

    id: Mapped[uuid.UUID] = uuid_pk()
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    gatilho: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    condicoes: Mapped[list[dict]] = mapped_column(JSONB, nullable=False, default=list)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    actions: Mapped[list["WorkflowAction"]] = relationship(
        back_populates="workflow", cascade="all, delete-orphan", order_by="WorkflowAction.ordem"
    )


class WorkflowAction(Base):
    __tablename__ = "workflow_actions"

    id: Mapped[uuid.UUID] = uuid_pk()
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ordem: Mapped[int] = mapped_column(Integer, nullable=False)
    tipo_acao: Mapped[str] = mapped_column(String(40), nullable=False)
    parametros: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    workflow: Mapped[Workflow] = relationship(back_populates="actions")


class WorkflowExecutionLog(Base, TenantMixin):
    __tablename__ = "workflow_execution_logs"

    id: Mapped[uuid.UUID] = uuid_pk()
    # nullable + ON DELETE SET NULL: excluir o workflow não deve apagar o histórico de
    # execuções (comportamento explícito do protótipo aprovado) — por isso o nome também
    # fica congelado aqui, para o log continuar legível mesmo depois do workflow sumir.
    workflow_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("workflows.id", ondelete="SET NULL"), index=True
    )
    workflow_nome: Mapped[str] = mapped_column(String(120), nullable=False)
    entidade_ref: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    resultado: Mapped[str] = mapped_column(String(20), nullable=False)
    detalhes: Mapped[dict | None] = mapped_column(JSONB)
    executado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
