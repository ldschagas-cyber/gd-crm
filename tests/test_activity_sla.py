"""Testes de ActivitySlaService.estado_regra — a parte pura e sem banco do motor de SLA
Comercial (ver docs/PLANO_SLA_COMERCIAL.md §3). As consultas que cruzam Company/Task/Deal
(`_company_status_items`/`_milestone_items`/`_deal_stage_items`) dependem de sessão real com
tenant no contexto — sem fixture de banco neste repo hoje (mesmo racional de
test_funil_metas.py e test_commercial_intelligence.py para a parte que toca banco/rede)."""
import os
from datetime import datetime, timedelta, timezone

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from app.services.activity_sla import ActivitySlaService  # noqa: E402

AGORA = datetime(2026, 8, 12, 12, 0, tzinfo=timezone.utc)


def estado(gatilho_horas_atras, prazo_horas, cumprida_horas_atras=None):
    gatilho_em = AGORA - timedelta(hours=gatilho_horas_atras)
    cumprida_em = AGORA - timedelta(hours=cumprida_horas_atras) if cumprida_horas_atras is not None else None
    return ActivitySlaService.estado_regra(gatilho_em, prazo_horas, cumprida_em, agora=AGORA)


def test_dentro_do_prazo_e_fora_da_janela_de_risco_fica_em_andamento():
    # Gatilho há 2h, prazo de 24h -> restam 22h (91% do prazo) -> bem longe do corte de 25%.
    r = estado(gatilho_horas_atras=2, prazo_horas=24)
    assert r["estado"] == "em_andamento"
    assert r["horas_atraso"] is None
    assert r["horas_restantes"] == 22.0


def test_dentro_do_prazo_mas_perto_do_limite_fica_em_risco():
    # Gatilho há 20h, prazo de 24h -> restam 4h (16.7% do prazo) -> abaixo do corte de 25%.
    r = estado(gatilho_horas_atras=20, prazo_horas=24)
    assert r["estado"] == "em_risco"
    assert r["horas_restantes"] == 4.0


def test_exatamente_no_corte_de_25_por_cento_conta_como_risco():
    # Gatilho há 18h, prazo de 24h -> restam exatamente 6h == 25% de 24h (fronteira <=).
    r = estado(gatilho_horas_atras=18, prazo_horas=24)
    assert r["estado"] == "em_risco"
    assert r["horas_restantes"] == 6.0


def test_prazo_vencido_sem_conclusao_fica_estourado():
    # Gatilho há 30h, prazo de 24h -> venceu há 6h.
    r = estado(gatilho_horas_atras=30, prazo_horas=24)
    assert r["estado"] == "estourado"
    assert r["horas_restantes"] is None
    assert r["horas_atraso"] == 6.0


def test_concluida_dentro_do_prazo_fica_cumprido():
    r = estado(gatilho_horas_atras=10, prazo_horas=24, cumprida_horas_atras=2)
    assert r["estado"] == "cumprido"
    assert r["horas_restantes"] is None
    assert r["horas_atraso"] is None


def test_concluida_depois_do_prazo_nao_conta_como_cumprida_fica_estourado():
    """Task concluída fora da janela (ex.: 40h atrás, quando o prazo de 24h já tinha vencido
    há 16h) não fecha a régua como cumprida — o SLA já tinha sido violado antes da conclusão
    tardia. `_cumprida_em` no service nunca devolveria essa data pra este cálculo em produção
    (a query já filtra >= gatilho e a primeira ocorrência ordenada asc seria anterior), mas o
    método puro precisa se comportar corretamente mesmo se receber uma data tardia."""
    r = estado(gatilho_horas_atras=40, prazo_horas=24, cumprida_horas_atras=0)
    assert r["estado"] == "estourado"
    assert r["horas_atraso"] == 16.0


def test_prazo_em_e_sempre_gatilho_mais_prazo_horas():
    gatilho_em = AGORA - timedelta(hours=5)
    r = ActivitySlaService.estado_regra(gatilho_em, 48, None, agora=AGORA)
    assert r["prazo_em"] == gatilho_em + timedelta(hours=48)
