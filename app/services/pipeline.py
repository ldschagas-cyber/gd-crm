"""Serviço de pipelines e etapas, incluindo a montagem do board (kanban)."""
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.models.pipeline import Pipeline, PipelineStage, StageType
from app.repositories.deal import DealRepository
from app.repositories.pipeline import PipelineRepository, StageRepository
from app.schemas.common import PageParams
from app.schemas.deal import DealRead
from app.schemas.pipeline import (
    BoardColumn, BoardResponse, PipelineCreate, PipelineUpdate, StageCreate, StageRead,
)


class PipelineService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = PipelineRepository(db)
        self.stages = StageRepository(db)
        self.deals = DealRepository(db)

    def list(self, params: PageParams) -> tuple[list[Pipeline], int]:
        return self.repo.list(offset=params.offset, limit=params.size, order_by=Pipeline.nome)

    def get(self, pipeline_id: UUID) -> Pipeline:
        pipeline = self.repo.get(pipeline_id)
        if pipeline is None:
            raise NotFoundError("Pipeline não encontrado")
        return pipeline

    def create(self, data: PipelineCreate) -> Pipeline:
        pipeline = Pipeline(nome=data.nome, is_default=data.is_default, cor_exibicao=data.cor_exibicao.value)
        pipeline = self.repo.add(pipeline)
        for i, st in enumerate(data.stages):
            stage = PipelineStage(
                pipeline_id=pipeline.id, nome=st.nome, ordem=st.ordem or i,
                tipo=st.tipo.value, sla_horas=st.sla_horas, probabilidade=st.probabilidade,
                marco_funil=st.marco_funil.value if st.marco_funil else None,
            )
            self.stages.add(stage)
        self.db.refresh(pipeline)
        return pipeline

    def update(self, pipeline_id: UUID, data: PipelineUpdate) -> Pipeline:
        pipeline = self.get(pipeline_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            if field == "cor_exibicao" and value is not None:
                value = value.value if hasattr(value, "value") else value
            setattr(pipeline, field, value)
        return self.repo.save(pipeline)

    def add_stage(self, pipeline_id: UUID, data: StageCreate) -> PipelineStage:
        self.get(pipeline_id)
        stage = PipelineStage(
            pipeline_id=pipeline_id, nome=data.nome, ordem=data.ordem,
            tipo=data.tipo.value, sla_horas=data.sla_horas, probabilidade=data.probabilidade,
            marco_funil=data.marco_funil.value if data.marco_funil else None,
        )
        return self.stages.add(stage)

    def update_stage(self, pipeline_id: UUID, stage_id: UUID, data: StageCreate) -> PipelineStage:
        stage = self.stages.get(stage_id)
        if stage is None or stage.pipeline_id != pipeline_id:
            raise NotFoundError("Etapa não encontrada")
        stage.nome = data.nome
        stage.ordem = data.ordem
        stage.tipo = data.tipo.value
        stage.sla_horas = data.sla_horas
        stage.probabilidade = data.probabilidade
        stage.marco_funil = data.marco_funil.value if data.marco_funil else None
        return self.stages.save(stage)

    def delete_stage(self, pipeline_id: UUID, stage_id: UUID) -> None:
        stage = self.stages.get(stage_id)
        if stage is None or stage.pipeline_id != pipeline_id:
            raise NotFoundError("Etapa não encontrada")
        if stage.tipo in (StageType.GANHO.value, StageType.PERDIDO.value):
            raise ConflictError("Etapas terminais (Ganho/Perdido) não podem ser excluídas")
        if self.deals.list_by_stage(stage_id):
            raise ConflictError("Existem negócios nesta etapa — mova-os antes de excluir")
        self.stages.delete(stage)

    def board(self, pipeline_id: UUID) -> BoardResponse:
        self.get(pipeline_id)
        stages = self.stages.list_by_pipeline(pipeline_id)
        columns = []
        for stage in stages:
            deals = self.deals.list_by_stage(stage.id)
            columns.append(BoardColumn(
                stage=StageRead.model_validate(stage),
                deals=[DealRead.model_validate(d) for d in deals],
            ))
        return BoardResponse(pipeline_id=pipeline_id, columns=columns)
