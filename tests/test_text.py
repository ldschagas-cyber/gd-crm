"""Testes de normalize_company_name — cobre os exemplos do requisito e as
regras de espaçamento, siglas, naturezas jurídicas e delimitadores de
sub-palavra (hífen/apóstrofo/barra). Função pura, sem dependência de
app.core.config/database — não precisa do boilerplate de env vars usado nos
testes de serviço.
"""
from app.core.text import normalize_company_name


def test_conectivos_intermediarios_ficam_minusculos():
    assert normalize_company_name("CYBELAR COMERCIO E INDUSTRIA LTDA") == "Cybelar Comercio e Industria Ltda."


def test_multiplos_conectivos_intermediarios():
    entrada = "UDIACO COMERCIO E INDUSTRIA DE FERRO E ACO LTDA"
    assert normalize_company_name(entrada) == "Udiaco Comercio e Industria de Ferro e Aco Ltda."


def test_nao_mexe_em_acentuacao_existente():
    assert normalize_company_name("BLAU FARMACÊUTICA") == "Blau Farmacêutica"


def test_preserva_numero_e_capitaliza_letra_apos_digito():
    assert normalize_company_name("3M DO BRASIL LTDA") == "3M do Brasil Ltda."


def test_sigla_com_pontos_mantida_maiuscula():
    assert normalize_company_name("TRANSPORTES SÃO JOSÉ S.A.") == "Transportes São José S.A."


def test_espacos_duplicados_e_nas_pontas_sao_removidos():
    assert normalize_company_name("  CYBELAR   COMERCIO LTDA  ") == "Cybelar Comercio Ltda."


def test_conectivo_como_primeira_palavra_e_capitalizado():
    assert normalize_company_name("E OUTROS COMERCIO") == "E Outros Comercio"


def test_string_vazia_retorna_vazia():
    assert normalize_company_name("") == ""


def test_string_so_com_espacos_retorna_vazia():
    assert normalize_company_name("   ") == ""


def test_sigla_me_mantida_maiuscula_no_fim():
    assert normalize_company_name("PADARIA DO ZE ME") == "Padaria do Ze ME"


def test_sigla_epp_mantida_maiuscula():
    assert normalize_company_name("COMERCIO DE ROUPAS EPP") == "Comercio de Roupas EPP"


def test_limitada_por_extenso():
    assert normalize_company_name("INDUSTRIA QUIMICA LIMITADA") == "Industria Quimica Limitada"


def test_hifen_apostrofo_barra_capitalizam_apos_o_delimitador_sem_altera_lo():
    assert normalize_company_name("souza-lima e d'avila ltda") == "Souza-Lima e D'Avila Ltda."
