"""Testes de normalize_company_name — cobre os exemplos do requisito e as
regras de espaçamento, siglas, naturezas jurídicas e delimitadores de
sub-palavra (hífen/apóstrofo/barra). Função pura, sem dependência de
app.core.config/database — não precisa do boilerplate de env vars usado nos
testes de serviço.
"""
from app.core.text import dedupe_key, extract_domain, is_personal_email_domain, normalize_company_name


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


# ---- extract_domain / is_personal_email_domain / dedupe_key (dedupe de empresa) --------

def test_extract_domain_de_email():
    assert extract_domain("contato@acme.com.br") == "acme.com.br"


def test_extract_domain_de_url_com_protocolo_e_www():
    assert extract_domain("https://www.acme.com.br/contato") == "acme.com.br"


def test_extract_domain_de_url_sem_protocolo():
    assert extract_domain("acme.com.br") == "acme.com.br"


def test_extract_domain_remove_porta():
    assert extract_domain("http://acme.com.br:8080/x") == "acme.com.br"


def test_extract_domain_string_vazia_e_none_retornam_none():
    assert extract_domain("") is None
    assert extract_domain(None) is None


def test_extract_domain_sem_ponto_retorna_none():
    assert extract_domain("acme") is None


def test_is_personal_email_domain():
    assert is_personal_email_domain("gmail.com") is True
    assert is_personal_email_domain("acme.com.br") is False
    assert is_personal_email_domain(None) is False


def test_dedupe_key_ignora_acento_caixa_e_sufixo_juridico():
    assert dedupe_key("Cybelar Comércio e Indústria Ltda.") == dedupe_key("CYBELAR COMERCIO E INDUSTRIA LTDA")


def test_dedupe_key_ignora_pontuacao():
    assert dedupe_key("Acme S.A.") == dedupe_key("ACME SA")


def test_dedupe_key_vazio():
    assert dedupe_key("") == ""
    assert dedupe_key(None) == ""


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
