"""Chamadas à Microsoft Graph em nome do usuário conectado (E-mail/Calendário).

Token de acesso dura pouco (60-90min) — em vez de rastrear expiração, tenta a
chamada com o token salvo e, se a Graph responder 401, renova via
`refresh_token` (que a Microsoft rotaciona a cada uso) e tenta uma vez mais.
"""
from datetime import datetime, timedelta, timezone
from uuid import UUID

import requests
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError
from app.core.token_crypto import decrypt_token, encrypt_token
from app.models.user_integration import UserIntegration
from app.repositories.user_integration import UserIntegrationRepository
from app.services.ms_graph import GRAPH_SCOPES, get_msal_app

GRAPH_BASE = "https://graph.microsoft.com/v1.0"


class GraphClient:
    def __init__(self, db: Session):
        self.db = db
        self.integrations = UserIntegrationRepository(db)

    def _integration(self, user_id: UUID, tipo: str) -> UserIntegration:
        row = self.integrations.get_by_user_tipo(user_id, tipo)
        if row is None or not row.ativo:
            raise ConflictError(
                f"Conecte sua conta Microsoft 365 ({tipo}) em Preferências antes de usar isso."
            )
        return row

    def _refresh(self, row: UserIntegration) -> str:
        if not row.refresh_token_enc:
            raise ConflictError("Conexão expirada — reconecte sua conta Microsoft 365 em Preferências.")
        refresh_token = decrypt_token(row.refresh_token_enc)
        result = get_msal_app().acquire_token_by_refresh_token(refresh_token, scopes=GRAPH_SCOPES[row.tipo])
        if not result or "access_token" not in result:
            raise ConflictError("Conexão expirada — reconecte sua conta Microsoft 365 em Preferências.")
        row.access_token_enc = encrypt_token(result["access_token"])
        if result.get("refresh_token"):
            row.refresh_token_enc = encrypt_token(result["refresh_token"])
        self.integrations.save(row)
        return result["access_token"]

    def _call(self, user_id: UUID, tipo: str, method: str, path: str, **kwargs) -> dict:
        row = self._integration(user_id, tipo)
        token = decrypt_token(row.access_token_enc)
        resp = requests.request(
            method, f"{GRAPH_BASE}{path}", headers={"Authorization": f"Bearer {token}"}, timeout=15, **kwargs
        )
        if resp.status_code == 401:
            token = self._refresh(row)
            resp = requests.request(
                method, f"{GRAPH_BASE}{path}", headers={"Authorization": f"Bearer {token}"}, timeout=15, **kwargs
            )
        if resp.status_code >= 400:
            detail = (resp.json().get("error", {}).get("message") if resp.content else None) or str(resp.status_code)
            raise ConflictError(f"Microsoft Graph recusou a solicitação: {detail}")
        return resp.json() if resp.content else {}

    def send_mail(self, user_id: UUID, to: str, subject: str, body: str) -> None:
        self._call(user_id, "email", "POST", "/me/sendMail", json={
            "message": {
                "subject": subject,
                "body": {"contentType": "Text", "content": body},
                "toRecipients": [{"emailAddress": {"address": to}}],
            },
            "saveToSentItems": True,
        })

    def search_mail(self, user_id: UUID, email_address: str, top: int = 15) -> list[dict]:
        data = self._call(
            user_id, "email", "GET", "/me/messages",
            params={
                "$search": f'"participants:{email_address}"',
                "$top": top,
                "$select": "subject,bodyPreview,receivedDateTime,from,toRecipients",
            },
        )
        messages = data.get("value", [])
        messages.sort(key=lambda m: m.get("receivedDateTime", ""), reverse=True)
        return messages

    def list_upcoming_events(self, user_id: UUID, days: int = 7, limit: int = 10) -> list[dict]:
        now = datetime.now(timezone.utc)
        data = self._call(
            user_id, "calendario", "GET", "/me/calendarView",
            params={
                "startDateTime": now.isoformat(),
                "endDateTime": (now + timedelta(days=days)).isoformat(),
                "$orderby": "start/dateTime",
                "$select": "subject,start,end,isOnlineMeeting,onlineMeeting",
                "$top": limit,
            },
        )
        return data.get("value", [])

    def create_meeting(self, user_id: UUID, subject: str, start_iso: str, end_iso: str, with_teams: bool) -> dict:
        payload = {
            "subject": subject,
            "start": {"dateTime": start_iso, "timeZone": "America/Sao_Paulo"},
            "end": {"dateTime": end_iso, "timeZone": "America/Sao_Paulo"},
        }
        if with_teams:
            payload["isOnlineMeeting"] = True
            payload["onlineMeetingProvider"] = "teamsForBusiness"
        return self._call(user_id, "calendario", "POST", "/me/events", json=payload)
