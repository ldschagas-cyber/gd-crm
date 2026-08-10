"""Testes de ForecastService — cobre a parte determinística e sem banco: parsing de mês
(`_periodo_bounds`) e a agregação pura de pipeline/forecast/commit (`_aggregate`). Mesmo
racional de test_funil_metas.py: sem fixture de banco neste repo hoje."""
import os
from datetime import date
from types import SimpleNamespace
from uuid import uuid4

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import pytest  # noqa: E402

from app.core.exceptions import AppException  # noqa: E402
from app.services.forecast import ForecastService  # noqa: E402


def fake_deal(valor, prob, commit=False, responsavel_id=None):
    return SimpleNamespace(
        id=uuid4(), nome="Negócio teste", responsavel_id=responsavel_id or uuid4(),
        valor_previsto=valor, probabilidade=prob, commit=commit,
        data_prev_fechamento=date(2026, 8, 15),
    )


# ---- _periodo_bounds ---------------------------------------------------------

def test_periodo_bounds_mes_regular():
    start, end = ForecastService._periodo_bounds("2026-08")
    assert start == date(2026, 8, 1)
    assert end == date(2026, 9, 1)


def test_periodo_bounds_dezembro_vira_o_ano():
    start, end = ForecastService._periodo_bounds("2026-12")
    assert start == date(2026, 12, 1)
    assert end == date(2027, 1, 1)


def test_periodo_bounds_formato_invalido_levanta_app_exception():
    with pytest.raises(AppException, match="Mês inválido"):
        ForecastService._periodo_bounds("agosto/2026")


def test_periodo_bounds_mes_fora_do_range_levanta_app_exception():
    with pytest.raises(AppException, match="Mês inválido"):
        ForecastService._periodo_bounds("2026-13")


# ---- _aggregate: reproduz o exemplo do pedido (pipeline 200k / forecast 80k / commit 40k) --

def test_aggregate_bate_com_exemplo_do_pedido():
    rows = [
        (fake_deal(32000, 85, commit=True), "Distribuidora Rio Verde", "Ana Beatriz", "Negociação"),
        (fake_deal(8000, 90, commit=True), "Metalúrgica Andrade", "Ana Beatriz", "Proposta"),
        (fake_deal(28000, 45), "GrupoNexa Logística", "Carlos Eduardo", "Negociação"),
        (fake_deal(15000, 30), "Fresenius Componentes", "Carlos Eduardo", "Qualificação"),
        (fake_deal(40000, 35), "Construtora Bellver", "Mariana Souza", "Proposta"),
        (fake_deal(12000, 20), "Auto Peças Rondon", "Mariana Souza", "Primeiro contato"),
        (fake_deal(22000, 10), "Comércio Vitalle", "Rafael Lima", "Primeiro contato"),
        (fake_deal(18000, 15), "Indústria Kaspar", "Rafael Lima", "Qualificação"),
        (fake_deal(15000, 30), "Tech Solutions BR", "Ana Beatriz", "Proposta"),
        (fake_deal(10000, 30), "Vidraçaria Ideal", "Carlos Eduardo", "Primeiro contato"),
    ]
    resumo = ForecastService._aggregate("2026-08", rows)

    assert resumo.pipeline_total == 200000.0
    assert resumo.forecast_total == pytest.approx(80300.0)  # ~R$80 mil
    assert resumo.commit_total == 40000.0
    assert len(resumo.negocios) == 10


def test_aggregate_agrupa_por_vendedor():
    resp_a, resp_b = uuid4(), uuid4()
    rows = [
        (fake_deal(10000, 50, responsavel_id=resp_a), "Empresa 1", "Vendedor A", "Proposta"),
        (fake_deal(20000, 50, commit=True, responsavel_id=resp_a), "Empresa 2", "Vendedor A", "Proposta"),
        (fake_deal(5000, 20, responsavel_id=resp_b), "Empresa 3", "Vendedor B", "Contato"),
    ]
    resumo = ForecastService._aggregate("2026-08", rows)

    por_id = {v.responsavel_id: v for v in resumo.por_vendedor}
    assert por_id[resp_a].negocios == 2
    assert por_id[resp_a].pipeline == 30000.0
    assert por_id[resp_a].commit == 20000.0
    assert por_id[resp_b].negocios == 1
    assert por_id[resp_b].commit == 0.0
    # ordenado por pipeline desc
    assert resumo.por_vendedor[0].responsavel_id == resp_a


def test_aggregate_sem_negocios_retorna_zeros():
    resumo = ForecastService._aggregate("2026-08", [])
    assert resumo.pipeline_total == 0.0
    assert resumo.forecast_total == 0.0
    assert resumo.commit_total == 0.0
    assert resumo.por_vendedor == []
    assert resumo.negocios == []


def test_aggregate_negocio_sem_valor_ou_probabilidade_nao_quebra():
    rows = [(fake_deal(None, None), "Empresa", "Vendedor", "Contato")]
    resumo = ForecastService._aggregate("2026-08", rows)
    assert resumo.pipeline_total == 0.0
    assert resumo.forecast_total == 0.0
