"""Cadence / CadenceStep / CadenceEnrollment — Cadência de E-mails (RF011, §7.6)."""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantMixin, TimestampMixin, uuid_pk


class Cadence(Base, TenantMixin, TimestampMixin):
    __tablename__ = "cadences"

    id: Mapped[uuid.UUID] = uuid_pk()
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    pausar_em_resposta: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    criar_followup: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    followup_titulo: Mapped[str | None] = mapped_column(String(255))
    created_by: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    steps: Mapped[list["CadenceStep"]] = relationship(
        back_populates="cadence", cascade="all, delete-orphan", order_by="CadenceStep.ordem"
    )
    enrollments: Mapped[list["CadenceEnrollment"]] = relationship(
        back_populates="cadence", cascade="all, delete-orphan"
    )


class CadenceStep(Base):
    __tablename__ = "cadence_steps"

    id: Mapped[uuid.UUID] = uuid_pk()
    cadence_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("cadences.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ordem: Mapped[int] = mapped_column(Integer, nullable=False)
    dias_espera: Mapped[int] = mapped_column(Integer, nullable=False)
    template_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("email_templates.id"), nullable=False
    )

    cadence: Mapped[Cadence] = relationship(back_populates="steps")


class CadenceEnrollment(Base, TenantMixin):
    __tablename__ = "cadence_enrollments"

    id: Mapped[uuid.UUID] = uuid_pk()
    cadence_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("cadences.id", ondelete="CASCADE"), nullable=False, index=True
    )
    company_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("companies.id"))
    contact_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("contacts.id"))
    deal_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("deals.id"))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ativa")
    step_atual: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    pausado_motivo: Mapped[str | None] = mapped_column(String(60))
    iniciado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    cadence: Mapped[Cadence] = relationship(back_populates="enrollments")
