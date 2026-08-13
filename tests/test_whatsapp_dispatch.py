"""Testes de app/services/twilio_whatsapp.py e da parte pura (sem banco) de
app/services/sequence_dispatch.py:send_step_whatsapp — o "gate" que decide se
uma etapa de Sequência tipo=whatsapp pode enviar de verdade (Content Template
aprovado pela Meta + contato com WhatsApp + integração configurada) ou precisa
cair no fallback de Task manual.

`advance_due_steps` em si (o loop que decide Task vs. envio real e grava
TimelineEvent) não tem teste aqui pelo mesmo motivo de test_activity_sla.py e
test_funil_metas.py: não existe fixture de banco/tenant neste repo hoje."""
import os
from types import SimpleNamespace

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import pytest  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.services import twilio_whatsapp  # noqa: E402
from app.services.sequence_dispatch import send_step_whatsapp  # noqa: E402


def contact(whatsapp="11988887777"):
    return SimpleNamespace(whatsapp=whatsapp)


def template(content_sid="HXabc123", variaveis=("nome", "empresa")):
    return SimpleNamespace(whatsapp_content_sid=content_sid, variaveis_disponiveis=list(variaveis))


@pytest.fixture(autouse=True)
def _reset_twilio_settings():
    original = (settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN, settings.TWILIO_WHATSAPP_FROM)
    yield
    settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN, settings.TWILIO_WHATSAPP_FROM = original


def test_to_whatsapp_number_aplica_ddi_55_igual_ao_link_wa_me_do_frontend():
    # Mesma regra de ContatosPage.jsx/ContactDetailPage.jsx: `wa.me/55${onlyDigits}`.
    assert twilio_whatsapp.to_whatsapp_number("(11) 98888-7777") == "whatsapp:+5511988887777"


def test_is_configured_exige_as_tres_credenciais():
    settings.TWILIO_ACCOUNT_SID = None
    settings.TWILIO_AUTH_TOKEN = "token"
    settings.TWILIO_WHATSAPP_FROM = "whatsapp:+5511900000000"
    assert twilio_whatsapp.is_configured() is False

    settings.TWILIO_ACCOUNT_SID = "AC123"
    assert twilio_whatsapp.is_configured() is True


def test_send_step_whatsapp_sem_content_sid_nao_envia():
    """Template ainda não aprovado pela Meta (whatsapp_content_sid vazio) —
    nunca deve tentar enviar, é exatamente o gate de segurança contra mandar
    texto livre não aprovado."""
    enviado = send_step_whatsapp(contact(), template(content_sid=None), {"nome": "Ana"})
    assert enviado is False


def test_send_step_whatsapp_sem_contato_ou_sem_whatsapp_nao_envia():
    assert send_step_whatsapp(None, template(), {}) is False
    assert send_step_whatsapp(contact(whatsapp=None), template(), {}) is False


def test_send_step_whatsapp_sucesso_numera_variaveis_na_ordem_do_template(monkeypatch):
    chamadas = []

    def fake_send(to_numero_local, content_sid, content_variables):
        chamadas.append((to_numero_local, content_sid, content_variables))
        return "SMxxxxx"

    monkeypatch.setattr(twilio_whatsapp, "send_template_message", fake_send)

    valores = {"nome": "Ana Beatriz", "empresa": "Rio Verde", "cargo": "Gerente"}
    enviado = send_step_whatsapp(contact(), template(variaveis=("nome", "empresa")), valores)

    assert enviado is True
    assert chamadas == [("11988887777", "HXabc123", {"1": "Ana Beatriz", "2": "Rio Verde"})]


def test_send_step_whatsapp_erro_do_twilio_nao_propaga_excecao(monkeypatch):
    def fake_send(*_args, **_kwargs):
        raise RuntimeError("Twilio recusou o envio de WhatsApp: boom")

    monkeypatch.setattr(twilio_whatsapp, "send_template_message", fake_send)

    assert send_step_whatsapp(contact(), template(), {"nome": "Ana"}) is False
