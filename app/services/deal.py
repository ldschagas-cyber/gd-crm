"""Serviço de negócios: criação, movimentação de etapa e fechamento."""
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import delete as sa_delete, update as sa_update
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.cadence import CadenceEnrollment
from app.models.deal import Deal, DealStatus
from app.models.pipeline import StageType
from app.models.sequence import SequenceEnrollment
from app.models.task import Task
from app.models.timeline import TimelineEvent, TimelineType
from app.repositories.company import CompanyRepository
from app.repositories.deal import DealRepository
from app.repositories.pipeline import PipelineRepository, StageRepository
from app.schemas.common import PageParams
from app.schemas.deal import DealClose, DealCreate, DealStageMove, DealUpdate
from app.services.timeline import TimelineService
from app.services.workflow_events import publish_event


class DealService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = DealRepository(db)
        self.stages = StageRepository(db)
        self.pipelines = PipelineRepository(db)
        self.companies = CompanyRepository(db)
        self.timeline = TimelineService(db)

    def list(self, params: PageParams, pipeline_id: UUID | None = None,
             stage_id: UUID | None = None, status: str | None = None,
             responsavel_id: UUID | None = None, company_id: UUID | None = None,
             busca: str | None = None) -> tuple[list[Deal], int]:
        filters = []
        if pipeline_id:
            filters.append(Deal.pipeline_id == pipeline_id)
        if stage_id:
            filters.append(Deal.stage_id == stage_id)
        if status:
            filters.append(Deal.status == status)
        if responsavel_id:
            filters.append(Deal.responsavel_id == responsavel_id)
        if company_id:
            filters.append(Deal.company_id == company_id)
        if busca:
            filters.append(self.repo.search_filter(busca))
        return self.repo.list(*filters, offset=params.offset, limit=params.size,
                              order_by=Deal.created_at.desc())

    def get(self, deal_id: UUID) -> Deal:
        deal = self.repo.get(deal_id)
        if deal is None:
            raise NotFoundError("Negócio não encontrado")
        return deal

    def create(self, data: DealCreate) -> Deal:
        if self.companies.get(data.company_id) is None:
            raise NotFoundError("Empresa não encontrada")
        stage = self.stages.get(data.stage_id)
        if stage is None:
            raise NotFoundError("Etapa não encontrada")
        payload = data.model_dump()
        if payload.get("probabilidade") is None:
            payload["probabilidade"] = stage.probabilidade
        deal = Deal(**payload)
        deal = self.repo.add(deal)
        self.timeline.registrar(deal.company_id, TimelineType.PIPELINE.value,
                                "Negócio criado", deal.nome, deal_id=deal.id)
        pipeline = self.pipelines.get(deal.pipeline_id)
        publish_event(self.db, "negocio_criado", deal.id, {
            "pipeline": pipeline.nome if pipeline else None, "origem": deal.origem,
            "valor_previsto": float(deal.valor_previsto) if deal.valor_previsto is not None else None,
            "_entidade_tipo": "deal", "_company_id": str(deal.company_id),
        })
        return deal

    def update(self, deal_id: UUID, data: DealUpdate) -> Deal:
        deal = self.get(deal_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(deal, field, value)
        return self.repo.save(deal)

    def move_stage(self, deal_id: UUID, data: DealStageMove) -> Deal:
        deal = self.get(deal_id)
        nova = self.stages.get(data.stage_id)
        if nova is None or nova.pipeline_id != deal.pipeline_id:
            raise NotFoundError("Etapa inválida para o pipeline do negócio")
        anterior = self.stages.get(deal.stage_id)
        deal.stage_id = nova.id
        if nova.probabilidade is not None:
            deal.probabilidade = nova.probabilidade
        # Etapas terminais encerram o negócio automaticamente.
        if nova.tipo == StageType.GANHO.value:
            deal.status = DealStatus.GANHO.value
            deal.data_fechamento = datetime.now(timezone.utc)
        elif nova.tipo == StageType.PERDIDO.value:
            deal.status = DealStatus.PERDIDO.value
            deal.data_fechamento = datetime.now(timezone.utc)
        deal = self.repo.save(deal)
        self.timeline.registrar(
            deal.company_id, TimelineType.PIPELINE.value, "Movimentação de pipeline",
            f"{anterior.nome if anterior else '-'} -> {nova.nome}", deal_id=deal.id,
            meta={"de": str(deal.stage_id), "para": str(nova.id)},
        )
        pipeline = self.pipelines.get(deal.pipeline_id)
        publish_event(self.db, "mudanca_etapa", deal.id, {
            "etapa_destino": nova.nome, "pipeline": pipeline.nome if pipeline else None,
            "_entidade_tipo": "deal", "_company_id": str(deal.company_id),
        })
        return deal

    def close(self, deal_id: UUID, data: DealClose) -> Deal:
        deal = self.get(deal_id)
        deal.status = data.status.value
        deal.motivo_perda = data.motivo_perda if data.status == DealStatus.PERDIDO else None
        deal.data_fechamento = datetime.now(timezone.utc)
        # Move para a etapa terminal correspondente do pipeline, senão o board
        # continua mostrando o negócio fechado preso na etapa aberta antiga.
        terminal = next(
            (s for s in self.stages.list_by_pipeline(deal.pipeline_id) if s.tipo == data.status.value),
            None,
        )
        if terminal is not None:
            deal.stage_id = terminal.id
            if terminal.probabilidade is not None:
                deal.probabilidade = terminal.probabilidade
        deal = self.repo.save(deal)
        self.timeline.registrar(deal.company_id, TimelineType.PIPELINE.value,
                                f"Negócio {deal.status}", deal.motivo_perda, deal_id=deal.id)
        return deal

    def delete(self, deal_id: UUID) -> None:
        deal = self.get(deal_id)
        # Sem FK ondelete configurado em nenhuma dessas tabelas — apaga o histórico
        # (só existe em função do negócio) e desvincula o resto (tarefas/inscrições
        # continuam existindo, só perdem a referência ao negócio excluído).
        self.db.execute(sa_delete(TimelineEvent).where(TimelineEvent.deal_id == deal.id))
        self.db.execute(sa_update(Task).where(Task.deal_id == deal.id).values(deal_id=None))
        self.db.execute(sa_update(CadenceEnrollment).where(CadenceEnrollment.deal_id == deal.id).values(deal_id=None))
        self.db.execute(sa_update(SequenceEnrollment).where(SequenceEnrollment.deal_id == deal.id).values(deal_id=None))
        self.repo.delete(deal)
