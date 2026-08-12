"""ActivitySlaRule — regras de SLA Comercial (ver docs/PLANO_SLA_COMERCIAL.md).

Cobre os dois gatilhos que faltam no motor de SLA já existente (`PipelineStage.sla_horas`,
restrito a etapa de negócio): mudança de `CompanyStatus` e marco único por empresa. O
resultado das três origens (deal_stage/company_status/milestone) é unificado só na camada
de serviço (`app/services/activity_sla.py`) — aqui é só o schema das regras novas.
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin, uuid_pk


class SlaGatilhoTipo(str, enum.Enum):
    COMPANY_STATUS = "company_status"
    MILESTONE = "milestone"
    # deal_stage NÃO entra aqui — continua vivendo em PipelineStage.sla_horas; o motor de
    # cálculo só lê de lá e apresenta junto, sem duplicar a configuração.


class ActivitySlaRule(Base, TenantMixin, TimestampMixin):
    __tablename__ = "activity_sla_rules"

    id: Mapped[uuid.UUID] = uuid_pk()
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    gatilho_tipo: Mapped[str] = mapped_column(String(20), nullable=False)
    # CompanyStatus.value pros dois tipos de gatilho hoje (milestone também é ancorado num
    # status — ex. "cliente" — só que dispara uma vez só; ver ActivitySlaMilestoneHit).
    gatilho_valor: Mapped[str] = mapped_column(String(40), nullable=False)
    prazo_horas: Mapped[int] = mapped_column(Integer, nullable=False)
    # TaskType.value; None = qualquer tarefa concluída vinculada à empresa cumpre a régua.
    tipo_atividade_esperado: Mapped[str | None] = mapped_column(String(20))
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    ordem: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class ActivitySlaMilestoneHit(Base, TenantMixin, TimestampMixin):
    """Marca que uma regra `milestone` já disparou para uma empresa — dispara uma vez só
    (ex.: 1ª vez que vira cliente), não a cada reentrada no status (cliente → inativo →
    cliente de novo não deveria reabrir o marco)."""
    __tablename__ = "activity_sla_milestone_hits"
    __table_args__ = (
        UniqueConstraint("rule_id", "company_id", name="uq_sla_milestone_hit_rule_company"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    rule_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("activity_sla_rules.id"), nullable=False, index=True
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True
    )
    disparado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
