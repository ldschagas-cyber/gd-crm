"""Repositórios de pipeline e etapas."""
from uuid import UUID

from app.models.pipeline import Pipeline, PipelineStage
from app.repositories.base import BaseRepository


class PipelineRepository(BaseRepository[Pipeline]):
    model = Pipeline


class StageRepository(BaseRepository[PipelineStage]):
    model = PipelineStage

    def list_by_pipeline(self, pipeline_id: UUID) -> list[PipelineStage]:
        items, _ = self.list(
            PipelineStage.pipeline_id == pipeline_id,
            limit=1000,
            order_by=PipelineStage.ordem,
        )
        return items
