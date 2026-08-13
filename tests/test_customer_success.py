"""Testes de Customer Success — mesmo espírito de tests/test_revenue.py: só a parte
pura (funções sem I/O), sem infraestrutura de teste com banco. Cobre o motor de Health
Score (app/services/health_scoring.py) e o helper de soma de meses usado pela renovação
de Assinatura (app/services/subscription.py). Ver docs/PLANO_CUSTOMER_SUCCESS.md.
"""
import os
from datetime import date

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from app.services.engagement_scoring import DEFAULT_ENGAGEMENT_RULES, calcular_engajamento  # noqa: E402
from app.services.health_scoring import (  # noqa: E402
    DEFAULT_HEALTH_RULES, _calcular_financeiro, calcular_saude, faixa,
)
from app.services.subscription import _add_months  # noqa: E402


# ---- calcular_saude — composição dos quatro pilares ------------------------------

def test_calcular_saude_cliente_saudavel_combina_os_quatro_pilares_pelos_pesos():
    resultado = calcular_saude(
        eventos_tipos=["reuniao", "reuniao", "email"],  # 30+30+8 = 68 de engajamento bruto
        dias_desde_ultima_interacao=2,
        uso_percebido=90,
        ultima_satisfacao=95,
        dias_desde_ultimo_checkin=3,
        assinatura_status="ativa",
        dias_ate_renovacao=200,
        rules=DEFAULT_HEALTH_RULES,
    )
    # 68*0.30 + 90*0.25 + 95*0.20 + 100*0.25 = 20.4 + 22.5 + 19 + 25 = 86.9 -> 87
    assert resultado.engajamento == 68
    assert resultado.uso == 90
    assert resultado.satisfacao == 95
    assert resultado.financeiro == 100
    assert resultado.score == 87
    assert resultado.precisa_checkin is False
    assert faixa(resultado.score, DEFAULT_HEALTH_RULES) == "saudavel"


def test_calcular_saude_sem_nenhum_sinal_usa_neutro_em_vez_de_zerar_e_sinaliza_checkin():
    # Cliente recém-implantado: nunca teve check-in, nunca teve interação registrada,
    # ainda sem assinatura cadastrada — não pode ser tratado como "saúde zero".
    resultado = calcular_saude(
        eventos_tipos=[], dias_desde_ultima_interacao=None, uso_percebido=None,
        ultima_satisfacao=None, dias_desde_ultimo_checkin=None, assinatura_status=None,
        dias_ate_renovacao=None, rules=DEFAULT_HEALTH_RULES,
    )
    assert resultado.engajamento == 0  # isto sim é um sinal real: zero interação registrada
    assert resultado.uso == DEFAULT_HEALTH_RULES["uso_padrao_sem_checkin"]
    assert resultado.satisfacao == DEFAULT_HEALTH_RULES["satisfacao_padrao_sem_checkin"]
    assert resultado.financeiro == 70  # sem assinatura ainda — neutro, não penaliza
    # 0*0.30 + 50*0.25 + 50*0.20 + 70*0.25 = 12.5 + 10 + 17.5 = 40
    assert resultado.score == 40
    assert resultado.precisa_checkin is True
    assert faixa(resultado.score, DEFAULT_HEALTH_RULES) == "atencao"  # exatamente no corte


def test_calcular_saude_engajamento_reaproveita_a_mesma_formula_da_central_de_leads():
    eventos = ["ligacao", "nota", "nota"]
    esperado = calcular_engajamento(
        eventos_tipos=eventos, etapas_cadencia_concluidas=0,
        dias_desde_ultima_interacao=10, rules=DEFAULT_ENGAGEMENT_RULES,
    )
    resultado = calcular_saude(
        eventos_tipos=eventos, dias_desde_ultima_interacao=10, uso_percebido=50,
        ultima_satisfacao=50, dias_desde_ultimo_checkin=1, assinatura_status="ativa",
        dias_ate_renovacao=None, rules=DEFAULT_HEALTH_RULES,
    )
    assert resultado.engajamento == esperado.score


# ---- _calcular_financeiro — pilar financeiro isolado ------------------------------

def test_financeiro_assinatura_ativa_sem_risco_de_renovacao_fica_no_teto():
    pontos, _ = _calcular_financeiro(
        assinatura_status="ativa", dias_ate_renovacao=None,
        dias_desde_ultima_interacao=None, rules=DEFAULT_HEALTH_RULES,
    )
    assert pontos == 100


def test_financeiro_assinatura_pausada_aplica_penalidade_fixa():
    pontos, breakdown = _calcular_financeiro(
        assinatura_status="pausada", dias_ate_renovacao=None,
        dias_desde_ultima_interacao=None, rules=DEFAULT_HEALTH_RULES,
    )
    assert pontos == 100 - DEFAULT_HEALTH_RULES["penalidade_assinatura_pausada"]
    assert any("pausada" in item.criterio.lower() for item in breakdown)


def test_financeiro_assinatura_cancelada_zera_o_pilar():
    pontos, _ = _calcular_financeiro(
        assinatura_status="cancelada", dias_ate_renovacao=None,
        dias_desde_ultima_interacao=None, rules=DEFAULT_HEALTH_RULES,
    )
    assert pontos == 0


def test_financeiro_renovacao_proxima_sem_contato_recente_penaliza():
    pontos, breakdown = _calcular_financeiro(
        assinatura_status="ativa", dias_ate_renovacao=10,
        dias_desde_ultima_interacao=20,  # > dias_contato_recente_para_renovacao (14)
        rules=DEFAULT_HEALTH_RULES,
    )
    assert pontos == 100 - DEFAULT_HEALTH_RULES["penalidade_renovacao_sem_contato"]
    assert breakdown  # motivo do alerta fica registrado, não é só um número


def test_financeiro_renovacao_proxima_com_contato_recente_nao_penaliza():
    pontos, breakdown = _calcular_financeiro(
        assinatura_status="ativa", dias_ate_renovacao=10,
        dias_desde_ultima_interacao=5,  # <= dias_contato_recente_para_renovacao (14)
        rules=DEFAULT_HEALTH_RULES,
    )
    assert pontos == 100
    assert breakdown == []


def test_financeiro_renovacao_distante_nao_penaliza_mesmo_sem_contato():
    pontos, _ = _calcular_financeiro(
        assinatura_status="ativa", dias_ate_renovacao=90,
        dias_desde_ultima_interacao=200, rules=DEFAULT_HEALTH_RULES,
    )
    assert pontos == 100


# ---- faixa — rótulo de exibição ---------------------------------------------------

def test_faixa_cortes_saudavel_atencao_em_risco():
    assert faixa(70, DEFAULT_HEALTH_RULES) == "saudavel"
    assert faixa(69, DEFAULT_HEALTH_RULES) == "atencao"
    assert faixa(40, DEFAULT_HEALTH_RULES) == "atencao"
    assert faixa(39, DEFAULT_HEALTH_RULES) == "em_risco"
    assert faixa(0, DEFAULT_HEALTH_RULES) == "em_risco"


# ---- _add_months (AssinaturaService.renovar) --------------------------------------

def test_add_months_cruza_o_ano():
    assert _add_months(date(2026, 8, 13), 12) == date(2027, 8, 13)
    assert _add_months(date(2026, 11, 1), 3) == date(2027, 2, 1)


def test_add_months_lida_com_estouro_de_dia_sem_pular_de_mes():
    # 31/jan + 1 mês não pode virar 03/mar — trava no último dia de fevereiro.
    assert _add_months(date(2026, 1, 31), 1) == date(2026, 2, 28)  # 2026 não é bissexto
    assert _add_months(date(2024, 1, 31), 1) == date(2024, 2, 29)  # 2024 é bissexto
