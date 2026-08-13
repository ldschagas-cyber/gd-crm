"""Testes de RevenueService — cobre só a parte pura (_compute e os helpers de data), sem
banco, no mesmo espírito de tests/test_commercial_intelligence.py e
RevenueInvestmentService._compute. As consultas ao banco (_mrr_atual, _soma_delta, ...) não
são testadas aqui, mesmo racional do resto do projeto: sem infraestrutura de teste com banco.
"""
import os
from datetime import date

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from app.schemas.subscription import RevenuePeriodo  # noqa: E402
from app.services.revenue import RevenueService  # noqa: E402


def test_compute_movimento_misto_calcula_todos_os_indicadores():
    # MRR atual 10.000, e no período: +2000 novo, +800 expansão, -300 contração, -1000 churn.
    # MRR início = 10000 - (2000+800-300-1000) = 10000 - 1500 = 8500.
    resumo = RevenueService._compute(
        periodo=RevenuePeriodo.MES, mrr=10_000, ativas=8,
        novo=2000, expansao=800, contracao=-300, churn=-1000, reativacao=0,
        qtd_cancelados=1, ativas_inicio=7,
    )
    assert resumo.mrr == 10_000
    assert resumo.arr == 120_000
    assert resumo.novo_mrr == 2000
    assert resumo.expansao_mrr == 800
    assert resumo.contracao_mrr == -300
    assert resumo.churn_mrr == -1000
    assert resumo.net_novo_mrr == 1500
    # churn_receita = |−1000| / 8500 = 11.76%
    assert resumo.churn_receita_pct == round(1000 / 8500 * 100, 2)
    # churn_clientes = 1 cancelado / 7 ativas no início = 14.29%
    assert resumo.churn_clientes_pct == round(1 / 7 * 100, 2)
    # NRR = (8500 + 800 - 300 - 1000) / 8500 = 8000/8500
    assert resumo.nrr_pct == round(8000 / 8500 * 100, 2)
    assert resumo.arpa == round(10_000 / 8, 2)
    assert resumo.ltv is not None


def test_compute_sem_churn_no_periodo_ltv_fica_indefinido():
    resumo = RevenueService._compute(
        periodo=RevenuePeriodo.MES, mrr=5000, ativas=3,
        novo=1000, expansao=0, contracao=0, churn=0, reativacao=0,
        qtd_cancelados=0, ativas_inicio=3,
    )
    assert resumo.churn_receita_pct == 0.0
    assert resumo.ltv is None  # None, não um número enganoso (divisão por zero)


def test_compute_mrr_inicio_zero_nao_divide_por_zero():
    # Toda a base é novo MRR deste período — mrr_inicio reconstruído fica em 0.
    resumo = RevenueService._compute(
        periodo=RevenuePeriodo.MES, mrr=4000, ativas=2,
        novo=4000, expansao=0, contracao=0, churn=0, reativacao=0,
        qtd_cancelados=0, ativas_inicio=0,
    )
    assert resumo.churn_receita_pct == 0.0
    assert resumo.nrr_pct == 100.0  # guarda de mrr_inicio <= 0 — não divide por zero
    assert resumo.churn_clientes_pct == 0.0
    assert resumo.ltv is None


def test_compute_reativacao_entra_na_reconstrucao_do_mrr_inicio_mas_nao_no_net_publico():
    # MRR atual 5000, com +1000 de reativação e -500 de churn no período (mesmo período).
    # O indicador público net_novo_mrr não conta reativação (fórmula documentada no plano),
    # mas o MRR de início reconstruído precisa descontá-la — senão churn/NRR saem errados:
    # sem a reativação, mrr_inicio seria 5000-(-500)=5500 em vez de 4500, e
    # churn_receita_pct sairia 9.09% em vez dos 11.11% corretos.
    resumo = RevenueService._compute(
        periodo=RevenuePeriodo.MES, mrr=5000, ativas=5,
        novo=0, expansao=0, contracao=0, churn=-500, reativacao=1000,
        qtd_cancelados=1, ativas_inicio=5,
    )
    assert resumo.net_novo_mrr == -500  # não inclui a reativação
    assert resumo.churn_receita_pct == round(500 / 4500 * 100, 2)
    assert resumo.nrr_pct == round(4000 / 4500 * 100, 2)


def test_subtract_months_cruza_o_ano():
    assert RevenueService._subtract_months(date(2026, 1, 1), 1) == date(2025, 12, 1)
    assert RevenueService._subtract_months(date(2026, 3, 1), 3) == date(2025, 12, 1)
    assert RevenueService._subtract_months(date(2026, 8, 1), 0) == date(2026, 8, 1)


def test_end_of_month_cobre_fevereiro_e_dezembro():
    assert RevenueService._end_of_month(date(2026, 2, 1)) == date(2026, 2, 28)  # 2026 não é bissexto
    assert RevenueService._end_of_month(date(2026, 12, 1)) == date(2026, 12, 31)
    assert RevenueService._end_of_month(date(2026, 4, 1)) == date(2026, 4, 30)
