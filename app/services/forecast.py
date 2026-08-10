"""Previsão Comercial — pipeline, forecast ponderado e commit por vendedor.

Nenhum domínio novo: reaproveita Deal.valor_previsto/probabilidade/data_prev_fechamento
(já existentes) mais o campo Deal.commit (único acréscimo, ver docs/PLANO_PREVISAO_COMERCIAL.md).
Forecast usa a mesma fórmula já exibida hoje por etapa no Kanban de Negócios
(valor_previsto × probabilidade / 100), só que agregada por mês/vendedor.
"""
from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.context import get_current_tenant
from app.core.exceptions import AppException
from app.models.company import Company
from app.models.deal import Deal, DealStatus
from app.models.pipeline import PipelineStage
from app.models.user import User, UserRole
from app.schemas.forecast import ForecastNegocio, ForecastResumo, ForecastVendedor

GESTAO_PERFIS = {UserRole.ADMIN.value, UserRole.GESTOR.value}


class ForecastService:
    def __init__(self, db: Session):
        self.db = db
        self.tenant_id = get_current_tenant()

    def resumo(
        self, mes: str, current_user: User,
        pipeline_id: UUID | None = None, responsavel_id: UUID | None = None,
    ) -> ForecastResumo:
        start, end = self._periodo_bounds(mes)
        # Quem não é gestão só vê o próprio recorte — o filtro pedido na query é
        # ignorado e substituído (mesmo padrão de dashboards seller vs. commercial).
        if current_user.perfil not in GESTAO_PERFIS:
            responsavel_id = current_user.id

        filters = [
            Deal.tenant_id == self.tenant_id,
            Deal.status == DealStatus.ABERTO.value,
            Deal.data_prev_fechamento >= start,
            Deal.data_prev_fechamento < end,
        ]
        if pipeline_id:
            filters.append(Deal.pipeline_id == pipeline_id)
        if responsavel_id:
            filters.append(Deal.responsavel_id == responsavel_id)

        rows = self.db.execute(
            select(Deal, Company.razao_social, User.nome, PipelineStage.nome)
            .join(Company, Deal.company_id == Company.id)
            .join(User, Deal.responsavel_id == User.id)
            .join(PipelineStage, Deal.stage_id == PipelineStage.id)
            .where(*filters)
            .order_by(Deal.data_prev_fechamento)
        ).all()

        return self._aggregate(mes, rows)

    @staticmethod
    def _periodo_bounds(mes: str) -> tuple[date, date]:
        try:
            year, month = (int(p) for p in mes.split("-"))
            if not 1 <= month <= 12:
                raise ValueError
        except ValueError:
            raise AppException("Mês inválido — use o formato AAAA-MM")
        start = date(year, month, 1)
        end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
        return start, end

    @staticmethod
    def _aggregate(mes: str, rows: list[tuple[Deal, str, str, str]]) -> ForecastResumo:
        """Pura — recebe as linhas já carregadas (Deal, empresa, vendedor, etapa) e faz
        só a soma/agrupamento. Separada de resumo() pra ser testável sem banco."""
        negocios: list[ForecastNegocio] = []
        por_vendedor: dict[UUID, dict] = {}
        pipeline_total = forecast_total = commit_total = 0.0

        for deal, company_nome, resp_nome, stage_nome in rows:
            valor = float(deal.valor_previsto or 0)
            prob = deal.probabilidade or 0
            forecast_deal = valor * prob / 100

            pipeline_total += valor
            forecast_total += forecast_deal
            if deal.commit:
                commit_total += valor

            negocios.append(ForecastNegocio(
                id=deal.id, nome=deal.nome, company_nome=company_nome,
                responsavel_id=deal.responsavel_id, responsavel_nome=resp_nome,
                stage_nome=stage_nome, valor_previsto=valor, probabilidade=deal.probabilidade,
                data_prev_fechamento=deal.data_prev_fechamento, commit=deal.commit,
            ))

            v = por_vendedor.setdefault(deal.responsavel_id, {
                "nome": resp_nome, "negocios": 0, "pipeline": 0.0, "forecast": 0.0, "commit": 0.0,
            })
            v["negocios"] += 1
            v["pipeline"] += valor
            v["forecast"] += forecast_deal
            if deal.commit:
                v["commit"] += valor

        por_vendedor_list = [
            ForecastVendedor(
                responsavel_id=rid, nome=v["nome"], negocios=v["negocios"],
                pipeline=round(v["pipeline"], 2), forecast=round(v["forecast"], 2), commit=round(v["commit"], 2),
            )
            for rid, v in por_vendedor.items()
        ]
        por_vendedor_list.sort(key=lambda v: v.pipeline, reverse=True)

        return ForecastResumo(
            mes=mes, pipeline_total=round(pipeline_total, 2), forecast_total=round(forecast_total, 2),
            commit_total=round(commit_total, 2), por_vendedor=por_vendedor_list, negocios=negocios,
        )
