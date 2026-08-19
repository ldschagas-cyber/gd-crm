"""Utilitários de normalização de texto — nome de empresa (exibição e dedupe) e domínio."""
import unicodedata
from urllib.parse import urlparse

# Palavras de ligação: minúsculas, exceto quando forem a primeira palavra.
CONNECTIVE_WORDS = {
    "de", "da", "das", "do", "dos", "e", "em", "com", "para",
    "por", "na", "nas", "no", "nos", "ao", "aos",
}

# Siglas conhecidas (≤4 caracteres) mantidas totalmente em maiúsculas.
# Inclui siglas de clientes vistas na base em CAIXA ALTA (AGC/ABB/FCC/GV/OL) —
# em nomes 100% maiúsculos não dá pra distinguir sigla de palavra curta por
# heurística (ACO, ZE, SÃO), então essas ficam na whitelist explícita.
KNOWN_ACRONYMS = {
    "S.A.", "SA", "ME", "MEI", "EPP", "EIRELI", "CNPJ", "CPF", "CEP",
    "CTE", "NF", "NFE", "XML", "ERP", "TMS", "WMS", "YMS", "API", "TI", "TII",
    "AGC", "ABB", "FCC", "GV", "OL",
}

# Naturezas jurídicas com formatação própria (não seguem o Title Case padrão).
LEGAL_ENTITY_SUFFIXES = {
    "LTDA": "Ltda.",
    "LIMITADA": "Limitada",
}

# Caracteres que iniciam uma nova "sub-palavra" para fins de capitalização
# (ex.: "souza-lima" -> "Souza-Lima", "d'avila" -> "D'Avila"), sem serem
# removidos ou movidos — nunca alteramos hífen, barra ou apóstrofo em si.
WORD_BOUNDARY_CHARS = {"-", "/", "'"}


def _title_case(word: str) -> str:
    """Capitaliza a primeira letra do token e de cada sub-palavra após um
    WORD_BOUNDARY_CHARS, preservando dígitos e demais caracteres como estão
    (ex.: "3m" -> "3M", "souza-lima" -> "Souza-Lima").
    """
    chars = list(word)
    capitalize_next = True
    for i, ch in enumerate(chars):
        if ch.isalpha():
            chars[i] = ch.upper() if capitalize_next else ch.lower()
            capitalize_next = False
        elif ch in WORD_BOUNDARY_CHARS:
            capitalize_next = True
        # dígitos e demais caracteres não alteram o estado de capitalização.
    return "".join(chars)


def _format_word(word: str, is_first: bool, name_has_lower: bool) -> str:
    lower = word.lower()
    upper = word.upper()
    if upper in LEGAL_ENTITY_SUFFIXES:
        return LEGAL_ENTITY_SUFFIXES[upper]
    if upper in KNOWN_ACRONYMS:
        return upper
    if not is_first and lower in CONNECTIVE_WORDS:
        return lower
    # Sigla curta em CAIXA ALTA que se destaca num nome de caixa mista
    # (ex.: "GV do Brasil", "OL Plastic") é preservada — o autor a escreveu
    # assim de propósito. Num nome inteiro em CAIXA ALTA (name_has_lower=False)
    # não dá pra distinguir sigla de palavra curta (ACO, ZE, SÃO), então lá só
    # as siglas de KNOWN_ACRONYMS (acima) são mantidas. Conectivos em caixa alta
    # (DA/DE/...) ficam de fora e seguem para o Title Case normal.
    if name_has_lower and word.isupper() and word.isalpha() and len(word) <= 3 \
            and lower not in CONNECTIVE_WORDS:
        return word
    return _title_case(word)


def normalize_company_name(name: str) -> str:
    """Normaliza um nome de empresa para exibição: Title Case, mantendo
    palavras de ligação em minúsculas (exceto na primeira posição), siglas
    conhecidas (e siglas curtas em CAIXA ALTA num nome de caixa mista) em
    maiúsculas e naturezas jurídicas formatadas (LTDA -> Ltda.).

    Não corrige acentuação — isso não é responsabilidade desta função.
    Função pura, sem efeitos colaterais.
    """
    if not name:
        return ""
    # Preserva a caixa original de cada token (não faz .lower() global) para que
    # _format_word consiga reconhecer siglas em CAIXA ALTA — a comparação com
    # conectivos/sufixos é feita em minúsculas dentro de _format_word.
    name_has_lower = any(c.islower() for c in name)
    words = name.split()  # split() já colapsa espaços duplicados e faz trim
    return " ".join(_format_word(w, i == 0, name_has_lower) for i, w in enumerate(words))


# ---- Dedupe de empresa (import + cadastro manual) — ver app/services/company_dedupe.py ----

# Domínios de e-mail pessoal/gratuito — descartados na cascata de dedupe por domínio
# corporativo, pois não identificam uma empresa (dois clientes diferentes podem muito
# bem ter contato em @gmail.com).
PERSONAL_EMAIL_DOMAINS = {
    "gmail.com", "hotmail.com", "hotmail.com.br", "outlook.com", "outlook.com.br",
    "yahoo.com", "yahoo.com.br", "uol.com.br", "bol.com.br", "terra.com.br",
    "live.com", "icloud.com", "globo.com", "ig.com.br", "msn.com", "r7.com",
    "zipmail.com.br", "aol.com",
}

# Tokens de natureza jurídica ignorados na chave de comparação (dedupe_key) — diferente
# de LEGAL_ENTITY_SUFFIXES acima, que é para formatação de exibição, não comparação.
_DEDUPE_IGNORED_TOKENS = {"ltda", "me", "mei", "epp", "eireli", "sa"}


def extract_domain(value: str | None) -> str | None:
    """Extrai o domínio (minúsculas, sem 'www.') de uma URL (com ou sem protocolo) ou de
    um endereço de e-mail. Retorna None quando não dá pra reconhecer um domínio válido.

    Exemplos: "contato@acme.com.br" -> "acme.com.br"; "https://www.acme.com.br/x" ->
    "acme.com.br"; "acme.com.br" (sem protocolo) -> "acme.com.br"; "acme" -> None.
    """
    if not value:
        return None
    value = value.strip().lower()
    if not value:
        return None
    if "@" in value:
        host = value.rsplit("@", 1)[1]
    else:
        candidate = value if "//" in value else f"//{value}"
        host = urlparse(candidate).netloc or value
        host = host.split(":")[0]  # remove porta, se houver
    host = host.strip().strip("/")
    if host.startswith("www."):
        host = host[4:]
    if not host or "." not in host:
        return None
    return host


def is_personal_email_domain(domain: str | None) -> bool:
    """True se `domain` for um provedor de e-mail pessoal/gratuito (ver
    PERSONAL_EMAIL_DOMAINS) — usado pra ignorar esses domínios na cascata de dedupe."""
    return bool(domain) and domain.lower() in PERSONAL_EMAIL_DOMAINS


def dedupe_key(name: str | None) -> str:
    """Gera uma chave de comparação (não de exibição — ver normalize_company_name pra
    isso) pra detectar empresas com o "mesmo nome": minúsculas, sem acento, sem
    pontuação, sem naturezas jurídicas comuns (Ltda/ME/EPP/EIRELI/S.A.), espaços
    colapsados. "" ou None -> "".
    """
    if not name:
        return ""
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    ascii_name = ascii_name.lower()
    # "." é removido (não vira espaço) pra "S.A." colapsar em "sa" e cair no filtro de
    # sufixo jurídico abaixo, em vez de sobrar como dois tokens soltos "s"/"a".
    ascii_name = ascii_name.replace(".", "")
    cleaned = "".join(ch if ch.isalnum() or ch.isspace() else " " for ch in ascii_name)
    words = [w for w in cleaned.split() if w not in _DEDUPE_IGNORED_TOKENS]
    return " ".join(words)
