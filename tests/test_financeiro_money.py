"""Testes dos utilitários monetários do Financeiro (RN-F09 desconto calculado; RNF-06
Decimal + half-up). Puros, sem banco — mesmo espírito de tests/test_revenue.py."""
import os
from decimal import Decimal

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from app.core.money import desconto_pct, money, pct  # noqa: E402


def test_desconto_calculado_padrao():
    # 5500 -> 3960 = 28% (caso do protótipo, Cerâmica Itaboraí v4).
    assert desconto_pct(5500, 3960) == Decimal("28.000")


def test_desconto_zero_quando_sem_desconto():
    assert desconto_pct(4200, 4200) == Decimal("0.000")


def test_desconto_tabela_zero_nao_estoura():
    # Preço de tabela 0 não pode dividir por zero — desconto é 0%.
    assert desconto_pct(0, 0) == Decimal("0.000")


def test_desconto_fracionario_meio_a_meio():
    # 100 -> 89,99 => 10,01% (arredondado a 3 casas half-up).
    assert desconto_pct(100, Decimal("89.99")) == Decimal("10.010")


def test_money_half_up_2_casas():
    assert money("10.005") == Decimal("10.01")   # half-up, não banker's rounding
    assert money(3.335) == Decimal("3.34")       # via str, sem ruído binário do float


def test_money_none_vira_zero():
    assert money(None) == Decimal("0.00")


def test_pct_3_casas():
    assert pct("11.8005") == Decimal("11.801")
