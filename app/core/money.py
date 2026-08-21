"""Utilitários monetários do módulo Financeiro (RNF-06).

Todo cálculo de valor/desconto usa Decimal, nunca float; arredondamento half-up em 2
casas para valores e 3 casas para percentuais, aplicado só na fronteira de persistência.
"""
from decimal import ROUND_HALF_UP, Decimal

CENTAVO = Decimal("0.01")
PCT = Decimal("0.001")


def dec(value) -> Decimal:
    """Converte qualquer entrada numérica (float/str/Decimal) para Decimal de forma
    segura — via str para não herdar o ruído binário do float."""
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value or 0))


def money(value) -> Decimal:
    return dec(value).quantize(CENTAVO, rounding=ROUND_HALF_UP)


def pct(value) -> Decimal:
    return dec(value).quantize(PCT, rounding=ROUND_HALF_UP)


def desconto_pct(preco_tabela, preco_proposto) -> Decimal:
    """Desconto SEMPRE calculado (RN-F09): 1 - proposto/tabela, em %. Tabela zero -> 0%."""
    tabela = dec(preco_tabela)
    if tabela <= 0:
        return pct(0)
    proposto = dec(preco_proposto)
    return pct((Decimal(1) - proposto / tabela) * 100)
