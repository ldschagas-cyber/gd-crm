"""Pipeline e PipelineStage — funis e etapas."""
import enum
import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantMixin, TimestampMixin, uuid_pk


class StageType(str, enum.Enum):
    ABERTA = "aberta"
    GANHO = "ganho"
    PERDIDO = "perdido"


class StageColorMode(str, enum.Enum):
    """Como o nome da etapa é exibido no board/lista de Negócios e na config do Pipeline."""
    SEM_COR = "sem_cor"
    PONTO = "ponto"
    SELO = "selo"


class Pipeline(Base, TenantMixin, TimestampMixin):
    __tablename__ = "pipelines"

    id: Mapped[uuid.UUID] = uuid_pk()
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    cor_exibicao: Mapped[str] = mapped_column(
        String(20), nullable=False, default=StageColorMode.SEM_COR.value
    )

    stages: Mapped[list["PipelineStage"]] = relationship(
        back_populates="pipeline", cascade="all, delete-orphan", order_by="PipelineStage.ordem"
    )


class PipelineStage(Base, TenantMixin):
    __tablename__ = "pipeline_stages"

    id: Mapped[uuid.UUID] = uuid_pk()
    pipeline_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("pipelines.id"), nullable=False, index=True
    )
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    ordem: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tipo: Mapped[str] = mapped_column(String(20), nullable=False, default=StageType.ABERTA.value)
    sla_horas: Mapped[int | None] = mapped_column(Integer)
    probabilidade: Mapped[int | None] = mapped_column(Integer)

    pipeline: Mapped["Pipeline"] = relationship(back_populates="stages")
