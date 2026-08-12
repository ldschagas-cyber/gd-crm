"""Testes de RevenueInvestmentService — cobre a parte determinística e sem banco: parsing
de mês (`_periodo_bounds`) e o cálculo puro de CAC/ROI (`_compute`). Mesmo racional de
test_forecast.py/test_funil_metas.py: sem fixture de banco neste repo hoje — `cac_roi()`
depende de sessão real (lista investimentos + chama FunilMetasService.resumo()), não
testado aqui."""
import os

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from datetime import date  # noqa: E402

import pytest  # noqa: E402

from app.core.exceptions import AppException  # noqa: E402
from app.services.revenue_investment import RevenueInvestmentService  # noqa: E402


# ---- _periodo_bounds ---------------------------------------------------------

def test_periodo_bounds_mes_regular():
    start, end = RevenueInvestmentService._periodo_bounds("2026-08")
    assert start == date(2026, 8, 1)
    assert end == date(2026, 9, 1)


def test_periodo_bounds_dezembro_vira_o_ano():
    start, end = RevenueInvestmentService._periodo_bounds("2026-12")
    assert start == date(2026, 12, 1)
    assert end == date(2027, 1, 1)


def test_periodo_bounds_formato_invalido_levanta_app_exception():
    with pytest.raises(AppException, match="Mês inválido"):
        RevenueInvestmentService._periodo_bounds("agosto/2026")


def test_periodo_bounds_mes_fora_do_range_levanta_app_exception():
    with pytest.raises(AppException, match="Mês inválido"):
        RevenueInvestmentService._periodo_bounds("2026-13")


# ---- _compute: CAC/ROI puro ---------------------------------------------------

def test_compute_cac_e_roi_com_investimento_e_clientes():
    resumo = RevenueInvestmentService._compute(
        "2026-08", investimento_total=44200.0, clientes_novos=4, receita_realizada=52000.0,
    )
    assert resumo.cac == 11050.0
    assert resumo.roi == pytest.approx(17.65, abs=0.01)  # (52000 - 44200) / 44200 * 100


def test_compute_roi_negativo_quando_investimento_maior_que_receita():
    resumo = RevenueInvestmentService._compute(
        "2026-08", investimento_total=60000.0, clientes_novos=2, receita_realizada=24000.0,
    )
    assert resumo.roi < 0
    assert resumo.roi == pytest.approx(-60.0)


def test_compute_cac_none_quando_nao_ha_clientes_fechados():
    # None, não 0 — CAC indefinido é diferente de "custou zero pra adquirir cliente".
    resumo = RevenueInvestmentService._compute(
        "2026-08", investimento_total=18000.0, clientes_novos=0, receita_realizada=0.0,
    )
    assert resumo.cac is None


def test_compute_roi_none_quando_nao_ha_investimento_lancado():
    # None, não 0% — sem lançamento, ROI é indefinido, não "sem retorno".
    resumo = RevenueInvestmentService._compute(
        "2026-08", investimento_total=0.0, clientes_novos=4, receita_realizada=52000.0,
    )
    assert resumo.roi is None


def test_compute_tudo_zero_devolve_cac_e_roi_none():
    resumo = RevenueInvestmentService._compute(
        "2026-08", investimento_total=0.0, clientes_novos=0, receita_realizada=0.0,
    )
    assert resumo.cac is None
    assert resumo.roi is None
    assert resumo.investimento_total == 0.0


def test_compute_arredonda_valores():
    resumo = RevenueInvestmentService._compute(
        "2026-08", investimento_total=33333.333, clientes_novos=3, receita_realizada=100000.111,
    )
    assert resumo.investimento_total == 33333.33
    assert resumo.receita_realizada == 100000.11
    assert resumo.cac == round(33333.333 / 3, 2)
