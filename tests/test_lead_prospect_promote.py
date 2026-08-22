"""Testes de LeadProspectService.promote — foco no dedupe que evita recriar empresa já
existente (era o bug relatado: Adium com 4 cópias, Connectoway com 3). Não há fixture de
DB/TestClient neste repo (ver tests/test_company_dedupe.py), então isolamos a dependência
de banco com fakes e monkeypatch em find_duplicate_company / CompanyRepository."""
import uuid
from types import SimpleNamespace

import app.services.lead_prospect as lp_mod
from app.models.lead_prospect import LeadStatus
from app.services.lead_prospect import LeadProspectService


def _lead(**kw):
    base = dict(
        promoted_company_id=None, empresa="Adium", uf="SP", cnpj=None, site=None,
        email=None, segmento=None, setor=None, cidade=None, linkedin=None, telefone=None,
        faixa_funcionarios=None, faixa_faturamento=None, contato_sugerido=None,
        dor_sugerida=None, origem=None, inteligencia_comercial=None, status=LeadStatus.NOVO.value,
    )
    base.update(kw)
    return SimpleNamespace(**base)


def _service(lead):
    """LeadProspectService sem __init__ — injeta só o que promote() usa."""
    svc = object.__new__(LeadProspectService)
    svc.db = object()
    svc.repo = SimpleNamespace(save=lambda l: l)
    svc._get_orm = lambda _id: lead
    svc.to_read = lambda l: l
    return svc


def test_promote_reaproveita_empresa_existente(monkeypatch):
    existente = SimpleNamespace(id=uuid.uuid4())
    adicionadas = []

    class Repo:
        def __init__(self, _db):
            pass

        def add(self, company):
            adicionadas.append(company)
            company.id = uuid.uuid4()
            return company

    monkeypatch.setattr(lp_mod, "CompanyRepository", Repo)
    monkeypatch.setattr(lp_mod, "find_duplicate_company", lambda *a, **k: existente)

    lead = _lead()
    _service(lead).promote(uuid.uuid4(), uuid.uuid4())

    # Vinculou o lead à empresa que já existia, sem criar outra.
    assert lead.promoted_company_id == existente.id
    assert lead.status == LeadStatus.PROMOVIDO.value
    assert adicionadas == []


def test_promote_cria_quando_nao_ha_duplicata(monkeypatch):
    adicionadas = []
    agendadas = []

    class Repo:
        def __init__(self, _db):
            pass

        def add(self, company):
            adicionadas.append(company)
            company.id = uuid.uuid4()
            return company

    monkeypatch.setattr(lp_mod, "CompanyRepository", Repo)
    monkeypatch.setattr(lp_mod, "find_duplicate_company", lambda *a, **k: None)
    # schedule_sdr_argos é importado dentro do método (import local) — o alvo do
    # monkeypatch é o módulo real, não lp_mod.
    import app.services.sdr_argos as sdr_argos_mod
    monkeypatch.setattr(sdr_argos_mod, "schedule_sdr_argos", lambda db, company_id: agendadas.append(company_id))

    lead = _lead()
    _service(lead).promote(uuid.uuid4(), uuid.uuid4())

    # Sem duplicata, cria a empresa e aponta o lead pra ela.
    assert len(adicionadas) == 1
    assert lead.promoted_company_id == adicionadas[0].id
    assert lead.status == LeadStatus.PROMOVIDO.value
    # Handoff nível 1 -> nível 2: o SDR Argos é agendado pra rodar em background só quando
    # uma empresa NOVA nasce da promoção (nunca inteligencia_comercial copiada do lead).
    assert agendadas == [adicionadas[0].id]
    assert adicionadas[0].inteligencia_comercial is None


def test_promote_reaproveitando_empresa_nao_reagenda_sdr_argos(monkeypatch):
    """Reaproveitar uma empresa já existente não deve reprocessar o dossiê dela —
    schedule_sdr_argos só roda no ramo que cria empresa nova."""
    existente = SimpleNamespace(id=uuid.uuid4())
    agendadas = []

    monkeypatch.setattr(lp_mod, "CompanyRepository", lambda _db: SimpleNamespace(add=lambda c: c))
    monkeypatch.setattr(lp_mod, "find_duplicate_company", lambda *a, **k: existente)
    import app.services.sdr_argos as sdr_argos_mod
    monkeypatch.setattr(sdr_argos_mod, "schedule_sdr_argos", lambda db, company_id: agendadas.append(company_id))

    lead = _lead()
    _service(lead).promote(uuid.uuid4(), uuid.uuid4())

    assert lead.promoted_company_id == existente.id
    assert agendadas == []
