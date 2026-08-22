"""Testes de SdrArgosService — cobre os ramos determinísticos (resolução de benchmark,
sugestão de cadência, guard clauses antes de chamar a IA) e o agendamento do handoff
(schedule_sdr_argos). A chamada real à Anthropic não é mockada aqui — mesmo racional de
test_commercial_intelligence.py, do qual este arquivo reaproveita o padrão de teste."""
import os
from unittest.mock import MagicMock, patch

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import uuid  # noqa: E402
from types import SimpleNamespace  # noqa: E402

import pytest  # noqa: E402

import app.services.sdr_argos as sdr_argos_mod  # noqa: E402
from app.core.exceptions import ConflictError, NotFoundError  # noqa: E402
from app.services.sdr_argos import SdrArgosService, schedule_sdr_argos  # noqa: E402


def _service():
    """SdrArgosService sem __init__ real (sem Session/DB de verdade) — injeta só o que
    cada teste usa, mesmo padrão de test_lead_prospect_promote.py."""
    svc = object.__new__(SdrArgosService)
    svc.db = object()
    svc.repo = SimpleNamespace()
    svc.timeline = SimpleNamespace(registrar=lambda **kw: None)
    return svc


# ---- _resolver_benchmark (mesmos 3 ramos de CommercialIntelligenceService) ----------

def test_empresa_sem_setor_nao_chama_benchmark_client():
    with patch.object(sdr_argos_mod, "BenchmarkClient") as mock_client:
        resultado = _service()._resolver_benchmark(None)
    mock_client.assert_not_called()
    assert resultado.disponivel is False
    assert "sem setor" in resultado.motivo_indisponivel


def test_setor_sem_mapeamento_nao_chama_benchmark_client():
    with patch.object(sdr_argos_mod, "BenchmarkClient") as mock_client:
        resultado = _service()._resolver_benchmark("Serviços")
    mock_client.assert_not_called()
    assert resultado.disponivel is False
    assert "sem segmento" in resultado.motivo_indisponivel


def test_setor_mapeado_e_benchmark_disponivel():
    with patch.object(sdr_argos_mod, "BenchmarkClient") as mock_client:
        mock_client.return_value.listar_segmentos.return_value = [
            {"segmento": "INDUSTRIA", "segmento_rotulo": "Indústria", "frete_kg_medio": 0.38},
        ]
        resultado = _service()._resolver_benchmark("Plástico")
    assert resultado.disponivel is True
    assert resultado.segmento_diagnostico == "Indústria"
    assert resultado.frete_kg_medio == 0.38


def test_diagnostico_indisponivel_degrada_sem_propagar_excecao():
    with patch.object(sdr_argos_mod, "BenchmarkClient") as mock_client:
        mock_client.return_value.listar_segmentos.side_effect = ConflictError("Diagnóstico fora do ar")
        resultado = _service()._resolver_benchmark("Plástico")
    assert resultado.disponivel is False
    assert resultado.motivo_indisponivel == "Diagnóstico fora do ar"


# ---- _sugerir_cadencia — nunca inscreve, só monta o preview -------------------------

def test_sem_sequencia_ativa_nao_sugere_cadencia():
    svc = _service()
    svc.db = MagicMock()
    svc.db.execute.return_value.scalars.return_value.first.return_value = None
    company = SimpleNamespace(tenant_id=uuid.uuid4(), contato_sugerido=None)
    assert svc._sugerir_cadencia(company) is None


def test_com_sequencia_ativa_sugere_sem_inscrever():
    svc = _service()
    svc.db = MagicMock()
    sequence_id = uuid.uuid4()
    fake_sequence = SimpleNamespace(id=sequence_id, nome="Cadência Outbound — Indústria")
    svc.db.execute.return_value.scalars.return_value.first.return_value = fake_sequence
    company = SimpleNamespace(tenant_id=uuid.uuid4(), contato_sugerido="Marcos — Gerente de Logística")

    sugestao = svc._sugerir_cadencia(company)

    assert sugestao == {
        "sequence_id": str(sequence_id),
        "sequence_nome": "Cadência Outbound — Indústria",
        "contato_sugerido": "Marcos — Gerente de Logística",
    }
    # Nenhuma escrita foi feita — é só leitura para montar o preview (decisão travada nº 6:
    # o SDR Argos sugere, nunca inscreve).
    svc.db.add.assert_not_called()


# ---- guard clauses antes de qualquer chamada externa ---------------------------------

def test_empresa_nao_encontrada_levanta_not_found():
    svc = _service()
    svc.repo = SimpleNamespace(get=lambda _id: None)
    with pytest.raises(NotFoundError):
        svc._get_company(uuid.uuid4())


def test_empresa_soft_deletada_levanta_not_found():
    svc = _service()
    svc.repo = SimpleNamespace(get=lambda _id: SimpleNamespace(deleted_at="2026-01-01"))
    with pytest.raises(NotFoundError):
        svc._get_company(uuid.uuid4())


def test_sem_anthropic_api_key_levanta_conflict_error_antes_de_buscar_empresa(monkeypatch):
    """A checagem da chave falha antes de tocar no banco — mesma ordem de guard clauses de
    CommercialIntelligenceService.gerar()."""
    monkeypatch.setattr(sdr_argos_mod.settings, "ANTHROPIC_API_KEY", None)
    svc = _service()
    tocou_repo = []
    svc.repo = SimpleNamespace(get=lambda _id: tocou_repo.append(_id))
    with pytest.raises(ConflictError, match="ANTHROPIC_API_KEY"):
        svc._client()
    assert tocou_repo == []


# ---- schedule_sdr_argos — o handoff nível 1 -> nível 2 -------------------------------

def test_schedule_sem_tenant_no_contexto_nao_agenda_nada():
    # get_current_tenant é importado localmente dentro de schedule_sdr_argos — patchar a
    # origem (app.core.context) afeta esse import local, feito fresco a cada chamada.
    with patch("app.core.context.get_current_tenant", return_value=None):
        with patch.object(sdr_argos_mod, "event") as mock_event:
            schedule_sdr_argos(db=object(), company_id=uuid.uuid4())
    mock_event.listen.assert_not_called()


def test_schedule_com_tenant_registra_listener_after_commit():
    tenant_id, company_id, fake_db = uuid.uuid4(), uuid.uuid4(), object()
    with patch("app.core.context.get_current_tenant", return_value=tenant_id):
        with patch.object(sdr_argos_mod, "event") as mock_event:
            schedule_sdr_argos(db=fake_db, company_id=company_id)
    args, kwargs = mock_event.listen.call_args
    assert args[0] is fake_db
    assert args[1] == "after_commit"
    assert kwargs.get("once") is True or (len(args) > 3 and args[3] is True)


def test_callback_do_schedule_dispara_task_com_tenant_e_company_corretos():
    """O callback registrado em after_commit passa tenant_id e company_id (nessa ordem —
    ver comentário em run_sdr_argos_task sobre por que o tenant precisa vir explícito)."""
    tenant_id, company_id = uuid.uuid4(), uuid.uuid4()
    with patch("app.core.context.get_current_tenant", return_value=tenant_id):
        with patch.object(sdr_argos_mod.event, "listen") as mock_listen:
            schedule_sdr_argos(db=object(), company_id=company_id)
    callback = mock_listen.call_args[0][2]
    with patch("app.workers.tasks.run_sdr_argos_task") as mock_task:
        callback(None)
    mock_task.delay.assert_called_once_with(str(tenant_id), str(company_id))
