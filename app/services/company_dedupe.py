"""Cascata de dedupe de empresa — reutilizada em CompanyService.create e nas 3 tasks de
import (empresas, contatos, empresas+contatos): CNPJ exato -> domínio corporativo
(site/e-mail, ignorando provedores pessoais) -> nome normalizado + UF.

CNPJ é opcional no cadastro (ver Company.cnpj) — sem essa cascata, uma lista de
prospecção sem CNPJ (comum: listas compradas/pesquisadas) não teria proteção nenhuma
contra duplicidade, que era o Problema 1 relatado.
"""
from app.core.text import dedupe_key, extract_domain, is_personal_email_domain
from app.models.company import Company
from app.repositories.company import CompanyRepository


def find_duplicate_company(
    repo: CompanyRepository, *, razao_social: str, uf: str | None = None,
    cnpj: str | None = None, site: str | None = None, email: str | None = None,
    contato_email: str | None = None,
) -> Company | None:
    """Retorna a primeira empresa (do tenant atual, não deletada) que bate com algum dos
    3 sinais, ou None se nenhuma bater. Só localiza — quem chama decide o que fazer com o
    resultado (reaproveitar quando o responsável bate, rejeitar quando diverge): ver
    app/workers/tasks.py e CompanyService.create.
    """
    if cnpj:
        found = repo.get_by_cnpj(cnpj)
        if found:
            return found

    for raw in (site, email, contato_email):
        domain = extract_domain(raw)
        if domain and not is_personal_email_domain(domain):
            found = repo.get_by_domain(domain)
            if found:
                return found

    key = dedupe_key(razao_social)
    if key:
        for candidate in repo.find_by_uf_not_deleted(uf):
            if dedupe_key(candidate.razao_social) == key:
                return candidate
    return None
