"""Testes de CommercialIntelligenceService — cobre só os ramos determinísticos
(mapeamento setor→segmento, degradação graciosa quando o Diagnóstico não
responde ou não há mapeamento, e os guard clauses antes de chamar a IA).
A chamada real à Anthropic não é mockada aqui — mesmo racional de não ter
teste automatizado para LeadEnrichmentService hoje.
"""
import os
from unittest.mock import patch

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import json
from datetime import datetime, timezone

import pytest  # noqa: E402

from app.core.exceptions import ConflictError  # noqa: E402
from app.models.lead_prospect import LeadProspect  # noqa: E402
from app.schemas.lead_prospect import (  # noqa: E402
    CommercialIntelligenceBenchmark, CommercialIntelligencePerfil, CommercialIntelligenceRecord,
    CommercialIntelligenceResponse,
)
from app.services.commercial_intelligence import CommercialIntelligenceService  # noqa: E402


@pytest.fixture()
def service():
    return CommercialIntelligenceService()


def test_setor_sem_mapeamento_nao_chama_benchmark_client(service):
    with patch("app.services.commercial_intelligence.BenchmarkClient") as mock_client:
        resultado = service._resolver_benchmark("Serviços")
    mock_client.assert_not_called()
    assert resultado.disponivel is False
    assert "sem segmento" in resultado.motivo_indisponivel


def test_setor_mapeado_e_benchmark_disponivel(service):
    with patch("app.services.commercial_intelligence.BenchmarkClient") as mock_client:
        mock_client.return_value.listar_segmentos.return_value = [
            {"segmento": "DISTRIBUIDOR", "segmento_rotulo": "Distribuidor", "frete_kg_medio": 0.55},
        ]
        resultado = service._resolver_benchmark("Autopeças")
    assert resultado.disponivel is True
    assert resultado.segmento_diagnostico == "Distribuidor"
    assert resultado.frete_kg_medio == 0.55


def test_diagnostico_indisponivel_degrada_sem_propagar_excecao(service):
    with patch("app.services.commercial_intelligence.BenchmarkClient") as mock_client:
        mock_client.return_value.listar_segmentos.side_effect = ConflictError("Diagnóstico fora do ar")
        resultado = service._resolver_benchmark("Autopeças")
    assert resultado.disponivel is False
    assert resultado.motivo_indisponivel == "Diagnóstico fora do ar"


def test_lead_sem_setor_levanta_conflict_error_antes_de_qualquer_chamada_externa(service):
    lead = LeadProspect(empresa="Teste", setor=None)
    with pytest.raises(ConflictError, match="setor"):
        service.gerar(lead)


def test_sem_anthropic_api_key_levanta_conflict_error(service, monkeypatch):
    monkeypatch.setattr("app.services.commercial_intelligence.settings.ANTHROPIC_API_KEY", None)
    lead = LeadProspect(empresa="Teste", setor="Autopeças")
    with pytest.raises(ConflictError, match="ANTHROPIC_API_KEY"):
        service.gerar(lead)


def test_commercial_intelligence_record_serializa_e_desserializa_sem_perda():
    """Contrato de LeadProspectService.save_inteligencia_comercial /
    LeadProspect.inteligencia_comercial: o que sai de model_dump_json() aqui é
    exatamente o texto gravado na coluna, e o frontend faz JSON.parse nele —
    qualquer campo perdido no round-trip quebra a leitura no drawer/dossiê."""
    record = CommercialIntelligenceRecord(
        perfil=CommercialIntelligencePerfil(porte_estimado="~220 colaboradores", erp=None),
        benchmark=CommercialIntelligenceBenchmark(disponivel=True, segmento_pesquisado="Autopeças",
                                                    segmento_diagnostico="Distribuidor", frete_kg_medio=0.42),
        argumento="Argumento de teste.",
        gravado_em=datetime(2026, 8, 5, 14, 32, tzinfo=timezone.utc),
    )
    parsed = json.loads(record.model_dump_json())
    assert parsed["argumento"] == "Argumento de teste."
    assert parsed["perfil"]["porte_estimado"] == "~220 colaboradores"
    assert parsed["benchmark"]["frete_kg_medio"] == 0.42
    assert parsed["gravado_em"].startswith("2026-08-05T14:32:00")

    # e o inverso: CommercialIntelligenceResponse (o que o endpoint de geração devolve, e o
    # payload que o PATCH de gravação recebe) precisa caber em CommercialIntelligenceRecord
    # só com gravado_em a mais — sem exigir nenhum outro campo do cliente.
    response = CommercialIntelligenceResponse(**{k: v for k, v in parsed.items() if k != "gravado_em"})
    CommercialIntelligenceRecord(**response.model_dump(), gravado_em=datetime.now(timezone.utc))
