"""Testes do debounce (coalescing) da regeneração do resumo executivo.

Cobre só a decisão determinística de "quem enfileira a task" — a reserva da
janela via Redis SET NX e a limpeza — sem tocar na chamada real à Anthropic
(mesmo racional dos outros testes de IA, que não mockam o modelo)."""
import os
from unittest.mock import MagicMock, patch

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from uuid import uuid4  # noqa: E402

from app.services import company_ai  # noqa: E402


def test_primeiro_evento_reserva_janela_e_seguintes_nao():
    """SET NX: o 1º evento da janela seta a chave (True); os seguintes veem a
    chave já presente e não reservam (False) — só o 1º enfileira a regeneração."""
    tenant_id, company_id = uuid4(), uuid4()
    fake = MagicMock()
    # 1º SET NX cria a chave; do 2º em diante já existe -> None (falha do NX).
    fake.set.side_effect = [True, None, None]
    with patch.object(company_ai, "_redis", return_value=fake):
        assert company_ai._debounce_reserva_janela(tenant_id, company_id, 90) is True
        assert company_ai._debounce_reserva_janela(tenant_id, company_id, 90) is False
        assert company_ai._debounce_reserva_janela(tenant_id, company_id, 90) is False
    # TTL = janela + 60s de folga pra atraso de fila do worker.
    fake.set.assert_called_with(company_ai._debounce_key(tenant_id, company_id), "1", nx=True, ex=150)


def test_redis_indisponivel_nao_engole_regeneracao():
    """Se o Redis não responde, reserva retorna True (degrada para o comportamento
    antigo de regenerar) em vez de derrubar o commit ou perder a atualização."""
    tenant_id, company_id = uuid4(), uuid4()
    fake = MagicMock()
    fake.set.side_effect = RuntimeError("redis down")
    with patch.object(company_ai, "_redis", return_value=fake):
        assert company_ai._debounce_reserva_janela(tenant_id, company_id, 90) is True


def test_clear_debounce_apaga_a_chave():
    tenant_id, company_id = uuid4(), uuid4()
    fake = MagicMock()
    with patch.object(company_ai, "_redis", return_value=fake):
        company_ai.clear_resumo_debounce(tenant_id, company_id)
    fake.delete.assert_called_once_with(company_ai._debounce_key(tenant_id, company_id))


def test_clear_debounce_engole_falha_do_redis():
    fake = MagicMock()
    fake.delete.side_effect = RuntimeError("redis down")
    with patch.object(company_ai, "_redis", return_value=fake):
        company_ai.clear_resumo_debounce(uuid4(), uuid4())  # não deve levantar
