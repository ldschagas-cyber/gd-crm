"""Testes de find_duplicate_company — função pura o suficiente pra testar com um
repositório fake em memória (duck typing: a função só chama get_by_cnpj/get_by_domain/
find_by_uf_not_deleted, nunca SQL direto), sem depender de banco real (não há fixture
de DB/TestClient neste repo hoje — ver docstring de tests/test_revenue_investment.py).
"""
from types import SimpleNamespace

from app.services.company_dedupe import find_duplicate_company


class FakeCompanyRepository:
    def __init__(self, companies):
        self.companies = companies

    def get_by_cnpj(self, cnpj):
        return next((c for c in self.companies if c.cnpj == cnpj), None)

    def get_by_domain(self, domain):
        return next(
            (c for c in self.companies if domain in (c.site or "") or domain in (c.email or "")), None
        )

    def find_by_uf_not_deleted(self, uf):
        return [c for c in self.companies if uf is None or c.uf == uf]


def _company(**kw):
    base = dict(cnpj=None, site=None, email=None, razao_social="", uf=None, responsavel_id=None)
    base.update(kw)
    return SimpleNamespace(**base)


def test_bate_por_cnpj():
    existing = _company(cnpj="11222333000144")
    repo = FakeCompanyRepository([existing])
    assert find_duplicate_company(repo, razao_social="Outro Nome", cnpj="11222333000144") is existing


def test_bate_por_dominio_ignorando_email_pessoal():
    existing = _company(site="https://www.acme.com.br")
    repo = FakeCompanyRepository([existing])
    assert find_duplicate_company(repo, razao_social="X", email="contato@gmail.com") is None
    assert find_duplicate_company(repo, razao_social="X", email="contato@acme.com.br") is existing


def test_bate_por_dominio_do_contato_no_import_combinado():
    existing = _company(email="contato@acme.com.br")
    repo = FakeCompanyRepository([existing])
    assert find_duplicate_company(repo, razao_social="X", contato_email="joao@acme.com.br") is existing


def test_bate_por_nome_normalizado_e_uf():
    existing = _company(razao_social="Acme Comercio Ltda", uf="SP")
    repo = FakeCompanyRepository([existing])
    assert find_duplicate_company(repo, razao_social="ACME COMERCIO LTDA", uf="SP") is existing
    assert find_duplicate_company(repo, razao_social="ACME COMERCIO LTDA", uf="RJ") is None


def test_cnpj_tem_prioridade_sobre_dominio_e_nome():
    por_cnpj = _company(cnpj="11222333000144", razao_social="Nome Antigo")
    por_dominio = _company(site="acme.com.br", razao_social="Outro Nome")
    repo = FakeCompanyRepository([por_dominio, por_cnpj])
    achado = find_duplicate_company(
        repo, razao_social="Nome Novo", cnpj="11222333000144", site="acme.com.br",
    )
    assert achado is por_cnpj


def test_nenhum_sinal_bate():
    assert find_duplicate_company(FakeCompanyRepository([]), razao_social="Nova Empresa") is None
