"""Utilitários de normalização de texto — hoje, só nome de empresa."""

# Palavras de ligação: minúsculas, exceto quando forem a primeira palavra.
CONNECTIVE_WORDS = {
    "de", "da", "das", "do", "dos", "e", "em", "com", "para",
    "por", "na", "nas", "no", "nos", "ao", "aos",
}

# Siglas conhecidas (≤4 caracteres) mantidas totalmente em maiúsculas.
KNOWN_ACRONYMS = {
    "S.A.", "SA", "ME", "MEI", "EPP", "EIRELI", "CNPJ", "CPF", "CEP",
    "CTE", "NF", "NFE", "XML", "ERP", "TMS", "WMS", "YMS", "API", "TI", "TII",
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


def _format_word(word: str, is_first: bool) -> str:
    upper = word.upper()
    if upper in LEGAL_ENTITY_SUFFIXES:
        return LEGAL_ENTITY_SUFFIXES[upper]
    if upper in KNOWN_ACRONYMS:
        return upper
    if not is_first and word in CONNECTIVE_WORDS:
        return word
    return _title_case(word)


def normalize_company_name(name: str) -> str:
    """Normaliza um nome de empresa para exibição: Title Case, mantendo
    palavras de ligação em minúsculas (exceto na primeira posição), siglas
    conhecidas em maiúsculas e naturezas jurídicas formatadas (LTDA -> Ltda.).

    Não corrige acentuação — isso não é responsabilidade desta função.
    Função pura, sem efeitos colaterais.
    """
    if not name:
        return ""
    words = name.lower().split()  # split() já colapsa espaços duplicados e faz trim
    return " ".join(_format_word(w, i == 0) for i, w in enumerate(words))
