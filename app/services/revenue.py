"""RevenueService — indicadores de Receita Recorrente (MRR/ARR/Churn/Expansão/NRR/LTV).

Não recalcula por comparação de snapshots entre meses — soma a coluna `delta_mrr` do livro-
razão (`AssinaturaEvento`) por tipo/período, igual a um extrato bancário. Ver
docs/PLANO_RECEITA_RECORRENTE.md §2. `_compute` é pura (só recebe números já apurados) pra
ser testável sem banco — mesmo espírito de `RevenueInvestmentService._compute` e
`ForecastService._aggregate`.
"""
from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.context import get_current_tenant
from app.models.subscription import Assinatura, AssinaturaEvento, AssinaturaStatus, TipoEventoAssinatura
from app.schemas.subscription import (
    RevenuePeriodo, RevenueResumo, RevenueWaterfall, RevenueWaterfallMes,
)


class RevenueService:
    def __init__(self, db: Session):
        self.db = db
        self.tenant_id = get_current_tenant()

    # ---- Resumo (stat-strip) ----------------------------------------------
    def resumo(self, periodo: RevenuePeriodo = RevenuePeriodo.MES) -> RevenueResumo:
        t = self.tenant_id
        start, end = self._periodo_bounds(periodo)

        mrr = self._mrr_atual(t)
        ativas = self._contagem_ativas(t)
        novo = self._soma_delta(t, start, end, TipoEventoAssinatura.NOVA.value)
        expansao = self._soma_delta(t, start, end, TipoEventoAssinatura.EXPANSAO.value)
        contracao = self._soma_delta(t, start, end, TipoEventoAssinatura.CONTRACAO.value)
        churn = self._soma_delta(t, start, end, TipoEventoAssinatura.CANCELAMENTO.value)
        reativacao = self._soma_delta(t, start, end, TipoEventoAssinatura.REATIVACAO.value)
        qtd_novos = self._contagem_tipo(t, start, end, TipoEventoAssinatura.NOVA.value)
        qtd_cancelados = self._contagem_tipo(t, start, end, TipoEventoAssinatura.CANCELAMENTO.value)
        qtd_reativados = self._contagem_tipo(t, start, end, TipoEventoAssinatura.REATIVACAO.value)
        ativas_inicio = max(ativas - qtd_novos - qtd_reativados + qtd_cancelados, 1 if ativas else 0)

        return self._compute(
            periodo, mrr, ativas, novo, expansao, contracao, churn, reativacao,
            qtd_cancelados, ativas_inicio,
        )

    @staticmethod
    def _compute(periodo: RevenuePeriodo, mrr: float, ativas: int, novo: float, expansao: float,
                 contracao: float, churn: float, reativacao: float, qtd_cancelados: int,
                 ativas_inicio: int) -> RevenueResumo:
        # MRR no início do período, reconstruído de trás pra frente a partir do MRR atual —
        # inclui reativação aqui (mesmo ela não aparecendo como categoria própria nos
        # indicadores públicos abaixo) porque é o único jeito de a reconstrução fechar certo.
        net_periodo_completo = novo + expansao + contracao + churn + reativacao
        mrr_inicio = mrr - net_periodo_completo

        churn_receita_pct = round(abs(churn) / mrr_inicio * 100, 2) if mrr_inicio > 0 else 0.0
        churn_clientes_pct = round(qtd_cancelados / ativas_inicio * 100, 2) if ativas_inicio > 0 else 0.0
        # NRR exclui MRR novo de propósito — mede só o que a base já existente rendeu.
        nrr_pct = (
            round((mrr_inicio + expansao + contracao + churn) / mrr_inicio * 100, 2)
            if mrr_inicio > 0 else 100.0
        )
        arpa = round(mrr / ativas, 2) if ativas else 0.0
        # None (não 0) quando não há churn no período — LTV fica indefinido, não infinito.
        ltv = round(arpa / (churn_receita_pct / 100), 2) if churn_receita_pct > 0 else None

        return RevenueResumo(
            periodo=periodo, mrr=round(mrr, 2), arr=round(mrr * 12, 2), assinaturas_ativas=ativas,
            novo_mrr=round(novo, 2), expansao_mrr=round(expansao, 2), contracao_mrr=round(contracao, 2),
            churn_mrr=round(churn, 2), net_novo_mrr=round(novo + expansao + contracao + churn, 2),
            churn_receita_pct=churn_receita_pct, churn_clientes_pct=churn_clientes_pct,
            nrr_pct=nrr_pct, arpa=arpa, ltv=ltv,
        )

    # ---- Waterfall mensal ---------------------------------------------------
    def waterfall(self, meses: int = 6) -> RevenueWaterfall:
        t = self.tenant_id
        hoje = date.today()
        primeiro_mes_atual = date(hoje.year, hoje.month, 1)

        itens = []
        for i in range(meses - 1, -1, -1):
            ref = self._subtract_months(primeiro_mes_atual, i)
            fim = self._end_of_month(ref)
            novo = self._soma_delta(t, ref, fim, TipoEventoAssinatura.NOVA.value)
            expansao = self._soma_delta(t, ref, fim, TipoEventoAssinatura.EXPANSAO.value)
            contracao = self._soma_delta(t, ref, fim, TipoEventoAssinatura.CONTRACAO.value)
            churn = self._soma_delta(t, ref, fim, TipoEventoAssinatura.CANCELAMENTO.value)
            itens.append(RevenueWaterfallMes(
                mes=f"{ref.year:04d}-{ref.month:02d}", novo_mrr=round(novo, 2),
                expansao_mrr=round(expansao, 2), contracao_mrr=round(contracao, 2),
                churn_mrr=round(churn, 2), net_mrr=round(novo + expansao + contracao + churn, 2),
            ))
        return RevenueWaterfall(meses=itens)

    # ---- Consultas ao banco --------------------------------------------------
    def _mrr_atual(self, t: UUID) -> float:
        return float(self.db.execute(
            select(func.coalesce(func.sum(Assinatura.valor_mensal), 0))
            .where(Assinatura.tenant_id == t, Assinatura.status == AssinaturaStatus.ATIVA.value)
        ).scalar_one())

    def _contagem_ativas(self, t: UUID) -> int:
        return self.db.execute(
            select(func.count()).select_from(Assinatura)
            .where(Assinatura.tenant_id == t, Assinatura.status == AssinaturaStatus.ATIVA.value)
        ).scalar_one()

    def _soma_delta(self, t: UUID, start: date, end: date, tipo: str) -> float:
        return float(self.db.execute(
            select(func.coalesce(func.sum(AssinaturaEvento.delta_mrr), 0))
            .where(AssinaturaEvento.tenant_id == t, AssinaturaEvento.tipo == tipo,
                   AssinaturaEvento.data_evento >= start, AssinaturaEvento.data_evento <= end)
        ).scalar_one())

    def _contagem_tipo(self, t: UUID, start: date, end: date, tipo: str) -> int:
        return self.db.execute(
            select(func.count()).select_from(AssinaturaEvento)
            .where(AssinaturaEvento.tenant_id == t, AssinaturaEvento.tipo == tipo,
                   AssinaturaEvento.data_evento >= start, AssinaturaEvento.data_evento <= end)
        ).scalar_one()

    # ---- Datas ----------------------------------------------------------------
    @staticmethod
    def _periodo_bounds(periodo: RevenuePeriodo) -> tuple[date, date]:
        hoje = date.today()
        if periodo == RevenuePeriodo.MES:
            start = date(hoje.year, hoje.month, 1)
        else:
            start = RevenueService._subtract_months(date(hoje.year, hoje.month, 1), 11)
        return start, hoje

    @staticmethod
    def _subtract_months(d: date, months: int) -> date:
        month = d.month - months
        year = d.year
        while month <= 0:
            month += 12
            year -= 1
        return date(year, month, 1)

    @staticmethod
    def _end_of_month(d: date) -> date:
        if d.month == 12:
            return date(d.year, 12, 31)
        return date(d.year, d.month + 1, 1) - timedelta(days=1)
