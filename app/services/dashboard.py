"""Serviço de dashboards: agregações comerciais e do vendedor."""
from datetime import datetime, timezone
from statistics import mean
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.context import get_current_tenant
from app.models.cadence import Cadence, CadenceEnrollment
from app.models.company import Company, CompanyStatus
from app.models.deal import Deal, DealStatus
from app.models.pipeline import Pipeline, PipelineStage
from app.models.sequence import Sequence, SequenceEnrollment
from app.models.task import Task, TaskStatus, TaskType
from app.schemas.dashboard import (
    CommercialDashboard,
    FunnelStage,
    Periodo,
    SellerDashboard,
    SequenceExecutionBreakdown,
    SlaBreach,
)


def _periodo_bounds(periodo: Periodo) -> tuple[datetime, datetime]:
    """Limites do período em UTC — não há timezone por tenant no sistema hoje."""
    now = datetime.now(timezone.utc)
    if periodo == Periodo.HOJE:
        start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    else:
        start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    return start, now


class DashboardService:
    def __init__(self, db: Session):
        self.db = db
        self.tenant_id = get_current_tenant()

    def _count(self, *filters) -> int:
        stmt = select(func.count()).select_from(Company.__table__ if False else Deal).where(*filters)
        return self.db.execute(stmt).scalar_one()

    def commercial(self, periodo: Periodo = Periodo.MES) -> CommercialDashboard:
        t = self.tenant_id
        start, now = _periodo_bounds(periodo)

        total_leads = self.db.execute(
            select(func.count()).select_from(Company)
            .where(Company.tenant_id == t, Company.status == CompanyStatus.LEAD.value,
                   Company.deleted_at.is_(None))
        ).scalar_one()
        qualificadas = self.db.execute(
            select(func.count()).select_from(Company)
            .where(Company.tenant_id == t, Company.status == CompanyStatus.QUALIFICADO.value,
                   Company.deleted_at.is_(None))
        ).scalar_one()
        negocios_ativos = self.db.execute(
            select(func.count()).select_from(Deal)
            .where(Deal.tenant_id == t, Deal.status == DealStatus.ABERTO.value)
        ).scalar_one()
        receita_prevista = self.db.execute(
            select(func.coalesce(func.sum(Deal.valor_previsto), 0))
            .where(Deal.tenant_id == t, Deal.status == DealStatus.ABERTO.value)
        ).scalar_one()
        negocios_criados = self.db.execute(
            select(func.count()).select_from(Deal)
            .where(Deal.tenant_id == t, Deal.created_at >= start, Deal.created_at < now)
        ).scalar_one()
        receita_ganha = self.db.execute(
            select(func.coalesce(func.sum(Deal.valor_previsto), 0))
            .where(Deal.tenant_id == t, Deal.status == DealStatus.GANHO.value,
                   Deal.data_fechamento >= start, Deal.data_fechamento < now)
        ).scalar_one()
        ganhos = self.db.execute(
            select(func.count()).select_from(Deal)
            .where(Deal.tenant_id == t, Deal.status == DealStatus.GANHO.value,
                   Deal.data_fechamento >= start, Deal.data_fechamento < now)
        ).scalar_one()
        total_fechados = self.db.execute(
            select(func.count()).select_from(Deal)
            .where(Deal.tenant_id == t, Deal.status.in_([DealStatus.GANHO.value, DealStatus.PERDIDO.value]),
                   Deal.data_fechamento >= start, Deal.data_fechamento < now)
        ).scalar_one()
        taxa = (ganhos / total_fechados * 100) if total_fechados else 0.0
        ticket = (float(receita_ganha) / ganhos) if ganhos else 0.0

        return CommercialDashboard(
            periodo=periodo, total_leads=total_leads, empresas_qualificadas=qualificadas,
            negocios_ativos=negocios_ativos, negocios_criados=negocios_criados,
            receita_prevista=float(receita_prevista), receita_ganha=float(receita_ganha),
            taxa_conversao=round(taxa, 2), ticket_medio=round(ticket, 2),
            funil=self._funnel(t), sla_estourado=self._sla_breaches(t),
            execucao_sequencias=self._sequence_execution(t),
        )

    def _funnel(self, t: UUID) -> list[FunnelStage]:
        pipeline = self.db.execute(
            select(Pipeline).where(Pipeline.tenant_id == t, Pipeline.ativo.is_(True))
            .order_by(Pipeline.is_default.desc(), Pipeline.created_at.asc())
        ).scalars().first()
        if pipeline is None:
            return []

        deals = self.db.execute(
            select(Deal).where(Deal.tenant_id == t, Deal.pipeline_id == pipeline.id,
                                Deal.status == DealStatus.ABERTO.value)
        ).scalars().all()
        by_stage: dict[UUID, list[Deal]] = {}
        for deal in deals:
            by_stage.setdefault(deal.stage_id, []).append(deal)

        now = datetime.now(timezone.utc)
        funil = []
        for stage in pipeline.stages:
            grupo = by_stage.get(stage.id, [])
            if grupo:
                horas = [(now - d.ultima_interacao).total_seconds() / 3600 for d in grupo]
                tempo_medio = round(mean(horas), 1)
            else:
                tempo_medio = None
            funil.append(FunnelStage(
                stage_id=stage.id, nome=stage.nome, ordem=stage.ordem,
                negocios_abertos=len(grupo), tempo_medio_parado_horas=tempo_medio,
                sla_horas=stage.sla_horas,
            ))
        return funil

    def _sla_breaches(self, t: UUID) -> list[SlaBreach]:
        now = datetime.now(timezone.utc)
        rows = self.db.execute(
            select(Deal, PipelineStage, Company)
            .join(PipelineStage, Deal.stage_id == PipelineStage.id)
            .join(Company, Deal.company_id == Company.id)
            .where(Deal.tenant_id == t, Deal.status == DealStatus.ABERTO.value,
                   PipelineStage.sla_horas.isnot(None))
        ).all()

        breaches = []
        for deal, stage, company in rows:
            horas_parado = (now - deal.ultima_interacao).total_seconds() / 3600
            atraso = horas_parado - stage.sla_horas
            if atraso > 0:
                breaches.append(SlaBreach(
                    deal_id=deal.id, nome=deal.nome, company_nome=company.razao_social,
                    stage_nome=stage.nome, horas_atraso=round(atraso, 1),
                ))
        breaches.sort(key=lambda b: b.horas_atraso, reverse=True)
        return breaches[:20]

    def _sequence_execution(self, t: UUID) -> list[SequenceExecutionBreakdown]:
        seq_rows = self.db.execute(
            select(Sequence.id, Sequence.nome, SequenceEnrollment.status, func.count())
            .join(SequenceEnrollment, SequenceEnrollment.sequence_id == Sequence.id)
            .where(Sequence.tenant_id == t, Sequence.ativo.is_(True))
            .group_by(Sequence.id, Sequence.nome, SequenceEnrollment.status)
        ).all()
        cad_rows = self.db.execute(
            select(Cadence.id, Cadence.nome, CadenceEnrollment.status, func.count())
            .join(CadenceEnrollment, CadenceEnrollment.cadence_id == Cadence.id)
            .where(Cadence.tenant_id == t, Cadence.ativo.is_(True))
            .group_by(Cadence.id, Cadence.nome, CadenceEnrollment.status)
        ).all()
        return self._pivot_execution(seq_rows, "sequence") + self._pivot_execution(cad_rows, "cadence")

    @staticmethod
    def _pivot_execution(rows, tipo: str) -> list[SequenceExecutionBreakdown]:
        grouped: dict[UUID, dict] = {}
        for id_, nome, status, count in rows:
            entry = grouped.setdefault(id_, {"nome": nome, "ativa": 0, "pausada": 0, "concluida": 0})
            if status in entry:
                entry[status] = count
        return [
            SequenceExecutionBreakdown(
                id=id_, nome=data["nome"], tipo=tipo,
                total=data["ativa"] + data["pausada"] + data["concluida"],
                ativa=data["ativa"], pausada=data["pausada"], concluida=data["concluida"],
            )
            for id_, data in grouped.items()
        ]

    def seller(self, user_id: UUID, periodo: Periodo = Periodo.MES) -> SellerDashboard:
        t = self.tenant_id
        start, now = _periodo_bounds(periodo)

        def task_count(*extra) -> int:
            return self.db.execute(
                select(func.count()).select_from(Task)
                .where(Task.tenant_id == t, Task.responsavel_id == user_id, *extra)
            ).scalar_one()

        pendentes = task_count(Task.status == TaskStatus.PENDENTE.value)
        concluidas = task_count(Task.status == TaskStatus.CONCLUIDA.value,
                                 Task.concluida_em >= start, Task.concluida_em < now)
        ligacoes = task_count(Task.tipo == TaskType.LIGACAO.value, Task.status == TaskStatus.CONCLUIDA.value,
                              Task.concluida_em >= start, Task.concluida_em < now)
        emails = task_count(Task.tipo == TaskType.EMAIL.value, Task.status == TaskStatus.CONCLUIDA.value,
                            Task.concluida_em >= start, Task.concluida_em < now)
        negocios_abertos = self.db.execute(
            select(func.count()).select_from(Deal)
            .where(Deal.tenant_id == t, Deal.responsavel_id == user_id,
                   Deal.status == DealStatus.ABERTO.value)
        ).scalar_one()
        receita = self.db.execute(
            select(func.coalesce(func.sum(Deal.valor_previsto), 0))
            .where(Deal.tenant_id == t, Deal.responsavel_id == user_id,
                   Deal.status == DealStatus.ABERTO.value)
        ).scalar_one()
        return SellerDashboard(
            periodo=periodo, tarefas_pendentes=pendentes, tarefas_concluidas=concluidas,
            ligacoes_realizadas=ligacoes, emails_enviados=emails,
            negocios_abertos=negocios_abertos, receita_prevista=float(receita),
        )
