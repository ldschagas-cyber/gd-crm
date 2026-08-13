"""Envio de WhatsApp via Twilio (WhatsApp Business Platform, BSP) para etapas de Sequência.

Config global do servidor (`TWILIO_WHATSAPP_FROM`, ao lado de TWILIO_ACCOUNT_SID/
TWILIO_AUTH_TOKEN já usados em Chamadas) — não por tenant nem por usuário, porque
o número WhatsApp Business é um só pra empresa toda (diferente do e-mail, onde
cada vendedor tem sua própria caixa Microsoft 365). Ver comentário em
app/core/config.py sobre a dependência de verificação da Meta Business Manager.

Toda mensagem iniciada pela empresa (o caso de Sequência/cadência fria) só pode
ser enviada com um Content Template pré-aprovado pela Meta — texto livre é
rejeitado pela API fora da janela de 24h de atendimento. Por isso este módulo
só expõe `send_template_message` (via `ContentSid`), nunca um envio de texto
livre; quem chama (`app/services/sequence_dispatch.py`) só tenta enviar quando
o `MessageTemplate` tem um `whatsapp_content_sid` explicitamente cadastrado —
ou seja, quando alguém já confirmou que aquele texto foi aprovado.
"""
import json
import re

import requests
from requests.auth import HTTPBasicAuth

from app.core.config import settings

MESSAGES_URL = "https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"


def is_configured() -> bool:
    return bool(settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN and settings.TWILIO_WHATSAPP_FROM)


def to_whatsapp_number(numero_local: str) -> str:
    """Mesma regra do link `wa.me` já usado no frontend (ContatosPage.jsx/
    ContactDetailPage.jsx): `contact.whatsapp` é gravado como DDD+número, sem
    DDI — sempre assume Brasil (+55)."""
    digitos = re.sub(r"\D", "", numero_local or "")
    return f"whatsapp:+55{digitos}"


def send_template_message(to_numero_local: str, content_sid: str, content_variables: dict[str, str]) -> str | None:
    """Retorna o MessageSid em sucesso, `None` se a config estiver ausente.
    Erros de rede/API sobem como exceção — quem chama (sequence_dispatch)
    trata com try/except, igual `send_step_email` faz pro Graph."""
    if not is_configured():
        return None
    resp = requests.post(
        MESSAGES_URL.format(sid=settings.TWILIO_ACCOUNT_SID),
        auth=HTTPBasicAuth(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN),
        data={
            "From": settings.TWILIO_WHATSAPP_FROM,
            "To": to_whatsapp_number(to_numero_local),
            "ContentSid": content_sid,
            "ContentVariables": json.dumps(content_variables),
        },
        timeout=15,
    )
    if resp.status_code >= 300:
        detail = resp.json().get("message") if resp.content else None
        raise RuntimeError(f"Twilio recusou o envio de WhatsApp: {detail or resp.status_code}")
    return resp.json().get("sid")
