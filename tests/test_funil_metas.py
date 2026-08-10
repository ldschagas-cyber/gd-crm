"""Testes de FunilMetasService — cobre a parte determinística e sem banco: parsing de
período e a cascata de metas/percentuais/status do Anexo 1 (`_montar_resumo`). As
consultas que cruzam LeadProspect/TimelineEvent/Deal (`_reais_atividade`/`_reais_coorte`)
dependem de sessão real com tenant no contexto — sem fixture de banco neste repo hoje
(mesmo racional de test_commercial_intelligence.py para o que chama a Anthropic de verdade).
"""
import os
from datetime import datetime, timezone

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import pytest  # noqa: E402

from app.core.exceptions import AppException  # noqa: E402
from app.schemas.funil_metas import DEFAULT_PCTS, ETAPAS_CHAVES, FunilMetasConfig  # noqa: E402
from app.services.funil_metas import FunilMetasService  # noqa: E402


@pytest.fixture()
def service():
    # BaseRepository/TenantService só guardam `db` no __init__ — nada aqui toca banco,
    # então None serve para exercitar os métodos puros (_periodo_bounds/_montar_resumo).
    return FunilMetasService(None)


def config_padrao() -> dict:
    return FunilMetasConfig().model_dump()


# ---- _periodo_bounds ---------------------------------------------------------

def test_periodo_bounds_mes_regular(service):
    start, end = service._periodo_bounds("2026-08")
    assert start == datetime(2026, 8, 1, tzinfo=timezone.utc)
    assert end == datetime(2026, 9, 1, tzinfo=timezone.utc)


def test_periodo_bounds_dezembro_vira_o_ano(service):
    start, end = service._periodo_bounds("2026-12")
    assert start == datetime(2026, 12, 1, tzinfo=timezone.utc)
    assert end == datetime(2027, 1, 1, tzinfo=timezone.utc)


def test_periodo_bounds_formato_invalido_levanta_app_exception(service):
    with pytest.raises(AppException, match="Mês inválido"):
        service._periodo_bounds("agosto/2026")


def test_periodo_bounds_mes_fora_do_range_levanta_app_exception(service):
    with pytest.raises(AppException, match="Mês inválido"):
        service._periodo_bounds("2026-13")


def test_resumo_modo_invalido_levanta_app_exception_antes_de_tocar_banco(service):
    with pytest.raises(AppException, match="Modo inválido"):
        service.resumo("trimestre", "2026-08")


# ---- _montar_resumo: cascata de metas -----------------------------------------

def test_montar_resumo_cascata_de_metas_bate_com_o_anexo_1(service):
    """Base 300 + percentuais default reproduz o Anexo 1 quase exatamente — só
    "decisores" arredonda 1 a menos (round(300*33%)=99, não 100), porque o Anexo 1
    guarda 33% já arredondado de 100/300=33,3%. Efeito colateral esperado da meta
    absoluta ser sempre *derivada* do percentual, nunca gravada solta (ver §5 do
    plano) — o restante da cascata (a partir de 99) bate exatamente."""
    config = {"empresas_pesquisadas_meta": 300, "etapas": [
        {"chave": c, "pct_etapa_anterior": DEFAULT_PCTS[c]} for c in ETAPAS_CHAVES
    ]}
    reais = {"pesquisadas": 300, "decisores": 99, "contatos": 50, "reunioes": 30,
             "diagnosticos": 20, "propostas": 15, "fechados": 10}
    resumo = service._montar_resumo("atividade", "2026-08", config, reais)

    metas = {e.chave: e.meta for e in resumo.etapas}
    assert metas == {"pesquisadas": 300, "decisores": 99, "contatos": 50, "reunioes": 30,
                      "diagnosticos": 20, "propostas": 15, "fechados": 10}
    # Real bateu a meta (derivada) em toda etapa -> nada crítico nem em atenção.
    assert all(e.status == "ok" for e in resumo.etapas)


def test_montar_resumo_etapa_muito_abaixo_da_meta_fica_critica(service):
    config = {"empresas_pesquisadas_meta": 300, "etapas": [
        {"chave": c, "pct_etapa_anterior": DEFAULT_PCTS[c]} for c in ETAPAS_CHAVES
    ]}
    # Reuniões: meta é 60% de "contatos" (40) = 24; real de 17 é 42,5% -> 17,5 p.p. abaixo.
    reais = {"pesquisadas": 312, "decisores": 96, "contatos": 40, "reunioes": 17,
             "diagnosticos": 12, "propostas": 9, "fechados": 6}
    resumo = service._montar_resumo("atividade", "2026-08", config, reais)

    por_chave = {e.chave: e for e in resumo.etapas}
    reunioes = por_chave["reunioes"]
    assert reunioes.status == "critico"
    assert reunioes.pct_real_etapa_anterior == pytest.approx(42.5, abs=0.1)
    assert reunioes.diferenca_pp == pytest.approx(-17.5, abs=0.1)

    # Diagnóstico (12/17 = 70,6%) ficou ACIMA da meta (67%) mesmo com volume baixo — não é
    # "crítico" só porque o número absoluto é pequeno, o controle é sobre a taxa.
    assert por_chave["diagnosticos"].status == "ok"


def test_montar_resumo_diferenca_moderada_fica_em_atencao(service):
    config = {"empresas_pesquisadas_meta": 100, "etapas": [
        {"chave": "decisores", "pct_etapa_anterior": 50},
        {"chave": "contatos", "pct_etapa_anterior": 50},
        {"chave": "reunioes", "pct_etapa_anterior": 50},
        {"chave": "diagnosticos", "pct_etapa_anterior": 50},
        {"chave": "propostas", "pct_etapa_anterior": 50},
        {"chave": "fechados", "pct_etapa_anterior": 50},
    ]}
    # decisores: real 42/100 = 42% vs meta 50% -> 8 p.p. abaixo -> "atenção" (entre -5 e -15).
    reais = {"pesquisadas": 100, "decisores": 42, "contatos": 0, "reunioes": 0,
             "diagnosticos": 0, "propostas": 0, "fechados": 0}
    resumo = service._montar_resumo("atividade", "2026-08", config, reais)
    decisores = next(e for e in resumo.etapas if e.chave == "decisores")
    assert decisores.status == "atencao"


def test_montar_resumo_etapa_base_sem_percentual_de_etapa_anterior(service):
    config = config_padrao()
    reais = {"pesquisadas": 300, "decisores": 0, "contatos": 0, "reunioes": 0,
             "diagnosticos": 0, "propostas": 0, "fechados": 0}
    resumo = service._montar_resumo("atividade", "2026-08", config, reais)
    pesquisadas = resumo.etapas[0]
    assert pesquisadas.chave == "pesquisadas"
    assert pesquisadas.pct_meta_etapa_anterior is None
    assert pesquisadas.pct_real_etapa_anterior is None
    assert pesquisadas.diferenca_pp is None
