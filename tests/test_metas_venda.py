"""Testes de MetasVendaService — parte determinística e sem banco: parsing de mês,
o status por atingimento e a soma da equipe (`_equipe_resumo`). As consultas que
cruzam Deal/SalesTarget dependem de sessão real com tenant no contexto — sem fixture
de banco neste repo hoje (mesmo racional de test_funil_metas.py).
"""
import os
from datetime import datetime, timezone
from uuid import uuid4

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import pytest  # noqa: E402

from app.core.exceptions import AppException  # noqa: E402
from app.schemas.metas_venda import VendedorMetaRow  # noqa: E402
from app.services.metas_venda import MetasVendaService, _status  # noqa: E402


@pytest.fixture()
def service():
    # Nada aqui toca banco — os métodos exercitados são puros.
    return MetasVendaService.__new__(MetasVendaService)


# ---- _mes_bounds -------------------------------------------------------------

def test_mes_bounds_regular(service):
    start, end = service._mes_bounds("2026-08")
    assert start == datetime(2026, 8, 1, tzinfo=timezone.utc)
    assert end == datetime(2026, 9, 1, tzinfo=timezone.utc)


def test_mes_bounds_dezembro_vira_o_ano(service):
    start, end = service._mes_bounds("2026-12")
    assert start == datetime(2026, 12, 1, tzinfo=timezone.utc)
    assert end == datetime(2027, 1, 1, tzinfo=timezone.utc)


def test_mes_bounds_invalido_levanta_app_exception(service):
    with pytest.raises(AppException, match="Mês inválido"):
        service._mes_bounds("2026-13")


# ---- _status -----------------------------------------------------------------

def test_status_sem_meta_e_none():
    assert _status(5, None) is None


def test_status_atingiu_ou_superou_meta_e_ok():
    assert _status(10, 10) == "ok"
    assert _status(12, 10) == "ok"


def test_status_meta_zero_e_ok():
    # Sem meta absoluta a comparar (0) não faz sentido punir — conta como ok.
    assert _status(0, 0) == "ok"


def test_status_entre_70_e_100_pct_e_atencao():
    assert _status(7, 10) == "atencao"
    assert _status(9, 10) == "atencao"


def test_status_abaixo_de_70_pct_e_critico():
    assert _status(6, 10) == "critico"
    assert _status(0, 10) == "critico"


# ---- _equipe_resumo: soma dos vendedores -------------------------------------

def _row(meta_qtd, meta_valor, real_qtd, real_valor):
    return VendedorMetaRow(
        user_id=uuid4(), nome="V", perfil="vendedor", team_id=None,
        meta_qtd=meta_qtd, meta_valor=meta_valor,
        realizado_qtd=real_qtd, realizado_valor=real_valor,
        status_qtd=_status(real_qtd, meta_qtd), status_valor=_status(real_valor, meta_valor),
    )


def test_equipe_resumo_soma_metas_e_realizados_dos_vendedores():
    vendedores = [
        _row(10, 50000, 8, 40000),
        _row(5, 20000, 6, 25000),
    ]
    equipe = MetasVendaService._equipe_resumo(uuid4(), "Alfa", "Gestor X", vendedores)
    assert equipe.meta_qtd == 15
    assert equipe.meta_valor == 70000
    assert equipe.realizado_qtd == 14
    assert equipe.realizado_valor == 65000
    # 14/15 qtd = 93% -> atenção; 65k/70k valor = 92,8% -> atenção.
    assert equipe.status_qtd == "atencao"
    assert equipe.status_valor == "atencao"


def test_equipe_resumo_vendedor_sem_meta_conta_realizado_mas_nao_meta():
    vendedores = [_row(None, None, 3, 12000)]
    equipe = MetasVendaService._equipe_resumo(None, "Sem equipe", None, vendedores)
    assert equipe.meta_qtd == 0
    assert equipe.meta_valor == 0
    assert equipe.realizado_qtd == 3
    assert equipe.realizado_valor == 12000
    # Sem meta na equipe (0) -> status neutro "ok" (não penaliza).
    assert equipe.status_qtd == "ok"
    assert equipe.status_valor == "ok"
