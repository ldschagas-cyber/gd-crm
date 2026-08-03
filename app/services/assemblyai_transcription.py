"""Transcrição de ligações via AssemblyAI (CRM → Preferências → Chamadas).

Fluxo: `record_recording_completed` (twilio_voice.py) agenda
`transcribe_call_recording_task` (Celery) assim que o Twilio confirma que a
gravação terminou. A task baixa o áudio (autenticado com as credenciais
Twilio), sobe pra AssemblyAI e submete a transcrição com `webhook_url` — a
AssemblyAI chama de volta `/public/assemblyai/transcript-webhook` quando
termina, e é aí (`handle_transcript_completed`) que o texto é gravado na
timeline e o áudio é apagado dos dois lados (local e Twilio). Decisão de
produto: só o texto fica retido, nunca o áudio.

Diarização é anônima (Locutor A/B) — a AssemblyAI não sabe identificar quem é
vendedor e quem é cliente, só separa vozes distintas.
"""
import re

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.context import set_current_tenant, set_current_user
from app.models.call import Call
from app.models.company import Company
from app.models.contact import Contact
from app.repositories.call import CallRepository
from app.repositories.timeline import TimelineRepository

SPEECH_MODELS = ["universal-3-5-pro", "universal-2"]
REDACT_PII_POLICIES = ["phone_number", "email_address", "credit_card_number", "banking_information"]
DOMAIN_KEYTERMS = ["GD Conecta", "CT-e", "frete"]


def is_configured() -> bool:
    return bool(settings.ASSEMBLYAI_API_KEY)


def _auth_headers() -> dict:
    return {"authorization": settings.ASSEMBLYAI_API_KEY}


def _webhook_url() -> str:
    base = (settings.TWILIO_VOICE_WEBHOOK_BASE_URL or "").rstrip("/")
    return f"{base}{settings.API_V1_PREFIX}/public/assemblyai/transcript-webhook"


def _keyterms_for_call(db: Session, call: Call) -> list[str]:
    keyterms = list(DOMAIN_KEYTERMS)
    if call.company_id:
        company = db.get(Company, call.company_id)
        if company:
            keyterms.append(company.razao_social)
    if call.contact_id:
        contact = db.get(Contact, call.contact_id)
        if contact:
            keyterms.append(contact.nome)
    return keyterms


def _download_twilio_recording(recording_url: str) -> bytes:
    """A `RecordingUrl` do Twilio sem extensão devolve o metadado JSON do recurso,
    não o áudio — precisa do sufixo `.mp3` pra baixar o arquivo de fato."""
    url = recording_url if re.search(r"\.(mp3|wav)$", recording_url) else f"{recording_url}.mp3"
    with httpx.Client(timeout=60.0) as client:
        response = client.get(url, auth=(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN))
        response.raise_for_status()
        return response.content


def _upload_to_assemblyai(audio_bytes: bytes) -> str:
    with httpx.Client(timeout=60.0) as client:
        response = client.post(
            f"{settings.ASSEMBLYAI_BASE_URL}/v2/upload",
            headers=_auth_headers(), content=audio_bytes,
        )
        response.raise_for_status()
        return response.json()["upload_url"]


def _submit_transcription(upload_url: str, keyterms: list[str]) -> str:
    payload = {
        "audio_url": upload_url,
        "speech_models": SPEECH_MODELS,
        "speaker_labels": True,
        "speaker_options": {"max_speakers_expected": 3},
        "language_code": "pt",
        "redact_pii": True,
        "redact_pii_policies": REDACT_PII_POLICIES,
        "redact_pii_sub": "entity_name",
        "keyterms_prompt": keyterms,
        "webhook_url": _webhook_url(),
    }
    if settings.ASSEMBLYAI_WEBHOOK_SECRET:
        payload["webhook_auth_header_name"] = "X-Webhook-Secret"
        payload["webhook_auth_header_value"] = settings.ASSEMBLYAI_WEBHOOK_SECRET
    with httpx.Client(timeout=30.0) as client:
        response = client.post(
            f"{settings.ASSEMBLYAI_BASE_URL}/v2/transcript",
            headers={**_auth_headers(), "content-type": "application/json"}, json=payload,
        )
        response.raise_for_status()
        return response.json()["id"]


def transcribe_and_submit(db: Session, call: Call, recording_url: str) -> str:
    """Baixa a gravação, sobe pra AssemblyAI e submete a transcrição — chamado
    pela task Celery `transcribe_call_recording_task`. Retorna o transcript_id
    (já gravado em `call.assemblyai_transcript_id` pra correlacionar o webhook
    de conclusão depois)."""
    audio_bytes = _download_twilio_recording(recording_url)
    upload_url = _upload_to_assemblyai(audio_bytes)
    keyterms = _keyterms_for_call(db, call)
    transcript_id = _submit_transcription(upload_url, keyterms)
    call.assemblyai_transcript_id = transcript_id
    db.flush()
    return transcript_id


def _fetch_transcript(transcript_id: str) -> dict:
    with httpx.Client(timeout=30.0) as client:
        response = client.get(
            f"{settings.ASSEMBLYAI_BASE_URL}/v2/transcript/{transcript_id}",
            headers=_auth_headers(),
        )
        response.raise_for_status()
        return response.json()


def _format_transcript(transcript: dict) -> str:
    utterances = transcript.get("utterances")
    if not utterances:
        return transcript.get("text") or ""
    linhas = [f"Locutor {u['speaker']}: {u['text']}" for u in utterances]
    return "\n".join(linhas)


def _delete_twilio_recording(recording_sid: str) -> None:
    url = f"https://api.twilio.com/2010-04-01/Accounts/{settings.TWILIO_ACCOUNT_SID}/Recordings/{recording_sid}.json"
    with httpx.Client(timeout=30.0) as client:
        response = client.delete(url, auth=(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN))
        # 404 é aceitável aqui — pode já ter sido apagada numa tentativa anterior.
        if response.status_code not in (204, 404):
            response.raise_for_status()


def handle_transcript_completed(db: Session, transcript_id: str, status: str) -> None:
    """Chamado pelo webhook público `/assemblyai/transcript-webhook`. Localiza a
    Call pelo transcript_id (sem tenant no contexto ainda), grava o texto (ou o
    erro) no TimelineEvent já existente daquela ligação e — só depois de
    confirmar sucesso — apaga a gravação do lado do Twilio, honrando a decisão
    de reter só o texto."""
    call = CallRepository(db).get_by_assemblyai_transcript_id_any_tenant(transcript_id)
    if call is None:
        return
    set_current_tenant(call.tenant_id)
    set_current_user(call.user_id)

    evento = TimelineRepository(db).get_by_call_sid(call.call_sid)

    if status == "error":
        transcript = _fetch_transcript(transcript_id)
        if evento is not None:
            evento.evento_meta = {
                **(evento.evento_meta or {}),
                "transcricao_status": "erro",
                "transcricao_erro": transcript.get("error"),
            }
        return

    transcript = _fetch_transcript(transcript_id)
    texto = _format_transcript(transcript)
    if evento is not None:
        evento.evento_meta = {
            **(evento.evento_meta or {}),
            "transcricao": texto,
            "transcricao_status": "concluida",
        }

    if call.recording_sid:
        _delete_twilio_recording(call.recording_sid)
        call.recording_sid = None
    db.flush()
