"""Serviço de negócios: criação, movimentação de etapa e fechamento."""
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import delete as sa_delete, update as sa_update
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.deal import Deal, DealStatus, DealTipo
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
             busca: str | None = None, contact_id: UUID | None = None) -> tuple[list[Deal], int]:
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
        if contact_id:
            filters.append(Deal.contact_id == contact_id)
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
        company = self.companies.get(data.company_id)
        if company is None:
            raise NotFoundError("Empresa não encontrada")
        stage = self.stages.get(data.stage_id)
        if stage is None:
            raise NotFoundError("Etapa não encontrada")
        payload = data.model_dump()
        if payload.get("probabilidade") is None:
            payload["probabilidade"] = stage.probabilidade
        # Origem não é escolhida no negócio — herda sempre da empresa (ver DealCreate/DealUpdate).
        payload["origem"] = company.origem
        payload["tipo"] = data.tipo.value
        deal = Deal(**payload)
        deal = self.repo.add(deal)
        # meta.para no formato de move_stage (§3 do PLANO_METAS_FUNIL.md) — permite
        # reconstruir "em que etapa esse negócio nasceu" com a mesma query que já lê
        # os eventos de movimentação, sem tratar criação como caso especial.
        self.timeline.registrar(deal.company_id, TimelineType.PIPELINE.value,
                                "Negócio criado", deal.nome, deal_id=deal.id,
                                meta={"para": str(deal.stage_id)})

        # Central de Leads: negócio criado é o gatilho automático de "convertido" — só
        # se a empresa já estava sendo acompanhada no funil (import tardio: evita ciclo).
        from app.services.company import CompanyService
        companies = CompanyService(self.db)
        companies.advance_funil_on_convertido(deal.company_id)
        # Customer Success: negócio de expansão aberto move o cliente pra "em_expansao"
        # enquanto a negociação dura (ver docs/PLANO_CUSTOMER_SUCCESS.md §4).
        if deal.tipo == DealTipo.EXPANSAO.value:
            companies.advance_cs_on_expansao_aberta(deal.company_id)

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
        ja_estava_ganho = deal.status == DealStatus.GANHO.value
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
        if nova.tipo in (StageType.GANHO.value, StageType.PERDIDO.value):
            self._on_deal_closed(deal, ja_estava_ganho=ja_estava_ganho)
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
        ja_estava_ganho = deal.status == DealStatus.GANHO.value
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
        self._on_deal_closed(deal, ja_estava_ganho=ja_estava_ganho)
        self.timeline.registrar(deal.company_id, TimelineType.PIPELINE.value,
                                f"Negócio {deal.status}", deal.motivo_perda, deal_id=deal.id)
        return deal

    def _on_deal_closed(self, deal: Deal, *, ja_estava_ganho: bool) -> None:
        """Gatilhos de Customer Success e Receita quando um negócio fecha (ganho ou
        perdido) — chamado tanto por move_stage (etapa terminal) quanto por close()
        (fechamento direto). Import tardio: evita ciclo com CompanyService. Ver
        docs/PLANO_CUSTOMER_SUCCESS.md §4.

        `ja_estava_ganho` protege a Receita de contar o mesmo negócio duas vezes: um
        negócio já ganho que é re-salvo (movido de volta pra etapa de ganho, fechado de
        novo) não deve gerar um segundo evento de MRR. Os gatilhos de CS são idempotentes
        por conta própria (guardas em advance_cs_*), então rodam de qualquer forma."""
        from app.services.company import CompanyService
        companies = CompanyService(self.db)
        if deal.status == DealStatus.GANHO.value:
            companies.advance_cs_on_deal_ganho(deal.company_id, deal.tipo, deal.responsavel_id)
            # Receita Recorrente: negócio ganho com valor cria/expande a assinatura do
            # cliente automaticamente (só na transição pra ganho, ver ja_estava_ganho).
            if not ja_estava_ganho:
                from app.services.subscription import AssinaturaService
                AssinaturaService(self.db).registrar_negocio_ganho(deal)
        if deal.tipo == DealTipo.EXPANSAO.value and deal.status in (DealStatus.GANHO.value, DealStatus.PERDIDO.value):
            companies.advance_cs_on_expansao_fechada(deal.company_id)

    def delete(self, deal_id: UUID) -> None:
        deal = self.get(deal_id)
        # Sem FK ondelete configurado em nenhuma dessas tabelas — apaga o histórico
        # (só existe em função do negócio) e desvincula o resto (tarefas/inscrições
        # continuam existindo, só perdem a referência ao negócio excluído).
        self.db.execute(sa_delete(TimelineEvent).where(TimelineEvent.deal_id == deal.id))
        self.db.execute(sa_update(Task).where(Task.deal_id == deal.id).values(deal_id=None))
        self.db.execute(sa_update(SequenceEnrollment).where(SequenceEnrollment.deal_id == deal.id).values(deal_id=None))
        self.repo.delete(deal)
