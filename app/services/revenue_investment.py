"""Investimento comercial + CAC/ROI — extensão de Previsão Comercial (ver
docs/PLANO_PREVISAO_COMERCIAL.md §8).

Não recalcula funil nem receita: lê clientes fechados / receita realizada de
FunilMetasService.resumo() (modo atividade) em vez de duplicar essas queries — mesmo
padrão de reaproveitamento que a própria Previsão Comercial já usa hoje pra
`fechados_valor_realizado` (ver app/services/forecast.py e app/services/funil_metas.py).
"""
from datetime import date
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.context import get_current_user_id
from app.core.exceptions import AppException, NotFoundError
from app.models.revenue_investment import RevenueInvestment
from app.repositories.revenue_investment import RevenueInvestmentRepository
from app.schemas.revenue_investment import CacRoiResumo, RevenueInvestmentCreate, RevenueInvestmentUpdate
from app.services.funil_metas import FunilMetasService


class RevenueInvestmentService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = RevenueInvestmentRepository(db)

    # ---- CRUD -----------------------------------------------------------
    def list(self, mes: str | None = None) -> list[RevenueInvestment]:
        filters = []
        if mes:
            start, end = self._periodo_bounds(mes)
            filters.append(RevenueInvestment.competencia >= start)
            filters.append(RevenueInvestment.competencia < end)
        items, _ = self.repo.list(*filters, limit=1000, order_by=RevenueInvestment.competencia.desc())
        return items

    def get(self, investment_id: UUID) -> RevenueInvestment:
        item = self.repo.get(investment_id)
        if item is None:
            raise NotFoundError("Lançamento de investimento não encontrado")
        return item

    def create(self, data: RevenueInvestmentCreate) -> RevenueInvestment:
        start, _ = self._periodo_bounds(data.mes)
        item = RevenueInvestment(
            competencia=start, categoria=data.categoria, valor=data.valor,
            observacao=data.observacao, criado_por=get_current_user_id(),
        )
        return self.repo.add(item)

    def update(self, investment_id: UUID, data: RevenueInvestmentUpdate) -> RevenueInvestment:
        item = self.get(investment_id)
        payload = data.model_dump(exclude_unset=True)
        for field, value in payload.items():
            setattr(item, field, value)
        return self.repo.save(item)

    def delete(self, investment_id: UUID) -> None:
        item = self.get(investment_id)
        self.repo.delete(item)

    # ---- CAC & ROI --------------------------------------------------------
    def cac_roi(self, mes: str) -> CacRoiResumo:
        investimento_total = round(sum(float(i.valor) for i in self.list(mes)), 2)

        funil = FunilMetasService(self.db).resumo("atividade", mes)
        fechados = next((e for e in funil.etapas if e.chave == "fechados"), None)
        clientes_novos = fechados.real if fechados else 0
        receita_realizada = float(funil.fechados_valor_realizado or 0)

        return self._compute(mes, investimento_total, clientes_novos, receita_realizada)

    @staticmethod
    def _compute(mes: str, investimento_total: float, clientes_novos: int, receita_realizada: float) -> CacRoiResumo:
        """Pura — recebe os três insumos já apurados e só faz a conta. Separada de
        cac_roi() pra ser testável sem banco (mesmo espírito de ForecastService._aggregate
        e FunilMetasService._montar_resumo)."""
        # None (não 0) quando o denominador é zero — CAC/ROI ficam indefinidos, não
        # "grátis"/"0%", que seria uma leitura enganosa (ninguém fechou negócio ainda, ou
        # ninguém lançou investimento ainda).
        cac = round(investimento_total / clientes_novos, 2) if clientes_novos else None
        roi = (
            round((receita_realizada - investimento_total) / investimento_total * 100, 2)
            if investimento_total else None
        )
        return CacRoiResumo(
            mes=mes, investimento_total=round(investimento_total, 2), clientes_novos=clientes_novos,
            receita_realizada=round(receita_realizada, 2), cac=cac, roi=roi,
        )

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
