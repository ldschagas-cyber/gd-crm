"""Serviço de dashboards: agregações comerciais e do vendedor."""
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.context import get_current_tenant
from app.models.company import Company, CompanyStatus
from app.models.deal import Deal, DealStatus
from app.models.task import Task, TaskStatus, TaskType
from app.schemas.dashboard import CommercialDashboard, SellerDashboard


class DashboardService:
    def __init__(self, db: Session):
        self.db = db
        self.tenant_id = get_current_tenant()

    def _count(self, *filters) -> int:
        stmt = select(func.count()).select_from(Company.__table__ if False else Deal).where(*filters)
        return self.db.execute(stmt).scalar_one()

    def commercial(self) -> CommercialDashboard:
        t = self.tenant_id
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
        receita_ganha = self.db.execute(
            select(func.coalesce(func.sum(Deal.valor_previsto), 0))
            .where(Deal.tenant_id == t, Deal.status == DealStatus.GANHO.value)
        ).scalar_one()
        ganhos = self.db.execute(
            select(func.count()).select_from(Deal)
            .where(Deal.tenant_id == t, Deal.status == DealStatus.GANHO.value)
        ).scalar_one()
        total_fechados = self.db.execute(
            select(func.count()).select_from(Deal)
            .where(Deal.tenant_id == t, Deal.status.in_([DealStatus.GANHO.value, DealStatus.PERDIDO.value]))
        ).scalar_one()
        taxa = (ganhos / total_fechados * 100) if total_fechados else 0.0
        ticket = (float(receita_ganha) / ganhos) if ganhos else 0.0
        return CommercialDashboard(
            total_leads=total_leads, empresas_qualificadas=qualificadas,
            negocios_ativos=negocios_ativos, receita_prevista=float(receita_prevista),
            receita_ganha=float(receita_ganha), taxa_conversao=round(taxa, 2),
            ticket_medio=round(ticket, 2),
        )

    def seller(self, user_id: UUID) -> SellerDashboard:
        t = self.tenant_id

        def task_count(*extra) -> int:
            return self.db.execute(
                select(func.count()).select_from(Task)
                .where(Task.tenant_id == t, Task.responsavel_id == user_id, *extra)
            ).scalar_one()

        pendentes = task_count(Task.status == TaskStatus.PENDENTE.value)
        concluidas = task_count(Task.status == TaskStatus.CONCLUIDA.value)
        ligacoes = task_count(Task.tipo == TaskType.LIGACAO.value,
                              Task.status == TaskStatus.CONCLUIDA.value)
        emails = task_count(Task.tipo == TaskType.EMAIL.value,
                            Task.status == TaskStatus.CONCLUIDA.value)
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
            tarefas_pendentes=pendentes, tarefas_concluidas=concluidas,
            ligacoes_realizadas=ligacoes, emails_enviados=emails,
            negocios_abertos=negocios_abertos, receita_prevista=float(receita),
        )
