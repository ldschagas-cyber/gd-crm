"""Serviço de Preferências pessoais: perfil, senha e integrações do próprio usuário."""
import uuid
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

import jwt
from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core import security
from app.core.config import settings
from app.core.context import set_current_tenant, set_current_user
from app.core.exceptions import AppException, ConflictError, UnauthorizedError
from app.core.token_crypto import encrypt_token
from app.models.user import User
from app.models.user_integration import UserIntegration
from app.repositories.user_integration import UserIntegrationRepository
from app.schemas.me import MeUpdate, PasswordChange, UpcomingMeetingRead
from app.services.graph_client import GraphClient
from app.services.ms_graph import GRAPH_SCOPES, get_msal_app

AVATAR_CONTENT_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


def _parse_graph_datetime(raw: str) -> datetime:
    """Graph devolve `start`/`end` sem timezone no valor (ex.: '...T12:30:00.0000000'),
    com o fuso em UTC por padrão (sem `Prefer: outlook.timezone` no request)."""
    return datetime.fromisoformat(raw[:26]).replace(tzinfo=timezone.utc)


class MeService:
    def __init__(self, db: Session):
        self.db = db
        self.integrations = UserIntegrationRepository(db)

    def update_profile(self, user: User, data: MeUpdate) -> User:
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(user, field, value)
        self.db.flush()
        self.db.refresh(user)
        return user

    def change_password(self, user: User, data: PasswordChange) -> None:
        if not security.verify_password(data.senha_atual, user.senha_hash):
            raise ConflictError("Senha atual incorreta")
        user.senha_hash = security.hash_password(data.senha_nova)
        self.db.flush()

    def get_integration(self, user: User, tipo: str) -> UserIntegration | None:
        return self.integrations.get_by_user_tipo(user.id, tipo)

    def get_authorize_url(self, user: User, tipo: str) -> str:
        """Monta a URL de consentimento da Microsoft para iniciar a conexão.

        O frontend navega o navegador de verdade pra essa URL (não é uma
        chamada AJAX) — o usuário loga e autoriza direto com a Microsoft, que
        devolve ele pro `callback` abaixo com um `code` de troca.
        """
        if not settings.MICROSOFT_CLIENT_ID or not settings.MICROSOFT_TENANT_ID:
            raise ConflictError(
                "Integração com Microsoft 365 ainda não configurada. "
                "Peça ao administrador do CRM para registrar o app no Azure AD."
            )
        if tipo not in GRAPH_SCOPES:
            raise AppException("Tipo de integração inválido.")

        state = security.create_ms_oauth_state(user.id, user.tenant_id, tipo)
        return get_msal_app().get_authorization_request_url(
            scopes=GRAPH_SCOPES[tipo],
            state=state,
            redirect_uri=settings.MICROSOFT_REDIRECT_URI,
        )

    def complete_integration(self, state: str, code: str) -> str:
        """Troca o `code` por tokens e grava a integração. Retorna o `tipo` conectado.

        Chamada a partir de uma rota pública (sem JWT de sessão — é o próprio
        redirect da Microsoft) — por isso fixa o contexto de tenant/usuário
        aqui a partir do `state`, no mesmo padrão do `get_current_user`.
        """
        try:
            payload = security.decode_token(state)
            if payload.get("type") != security.MS_OAUTH_STATE:
                raise UnauthorizedError("Solicitação de conexão inválida ou expirada.")
            user_id = UUID(payload["sub"])
            tenant_id = UUID(payload["tenant_id"])
            tipo = payload["tipo"]
        except (jwt.PyJWTError, KeyError, ValueError):
            raise UnauthorizedError("Solicitação de conexão inválida ou expirada.")

        set_current_tenant(tenant_id)
        set_current_user(user_id)

        result = get_msal_app().acquire_token_by_authorization_code(
            code, scopes=GRAPH_SCOPES[tipo], redirect_uri=settings.MICROSOFT_REDIRECT_URI,
        )
        if "access_token" not in result:
            raise AppException(result.get("error_description") or "Falha ao obter token da Microsoft.")

        access_enc = encrypt_token(result["access_token"])
        refresh_enc = encrypt_token(result["refresh_token"]) if result.get("refresh_token") else None

        existing = self.integrations.get_by_user_tipo(user_id, tipo)
        now = datetime.now(timezone.utc)
        if existing:
            existing.access_token_enc = access_enc
            existing.refresh_token_enc = refresh_enc
            existing.conectado_em = now
            existing.ativo = True
            self.integrations.save(existing)
        else:
            self.integrations.add(UserIntegration(
                user_id=user_id, tipo=tipo, provider="microsoft365",
                access_token_enc=access_enc, refresh_token_enc=refresh_enc,
                conectado_em=now, ativo=True,
            ))
        return tipo

    def disconnect_integration(self, user: User, tipo: str) -> None:
        existing = self.integrations.get_by_user_tipo(user.id, tipo)
        if existing:
            self.integrations.delete(existing)

    def upcoming_meetings(self, user: User, days: int = 7) -> list[UpcomingMeetingRead]:
        events = GraphClient(self.db).list_upcoming_events(user.id, days=days)
        return [
            UpcomingMeetingRead(
                assunto=e.get("subject") or "(sem assunto)",
                inicio=_parse_graph_datetime(e["start"]["dateTime"]),
                fim=_parse_graph_datetime(e["end"]["dateTime"]),
                teams_join_url=(e.get("onlineMeeting") or {}).get("joinUrl"),
            )
            for e in events
        ]

    def set_avatar(self, user: User, file: UploadFile) -> User:
        ext = AVATAR_CONTENT_TYPES.get(file.content_type)
        if ext is None:
            raise AppException("Envie uma imagem JPEG, PNG ou WebP.")
        content = file.file.read()
        max_bytes = settings.MAX_AVATAR_MB * 1024 * 1024
        if len(content) > max_bytes:
            raise AppException(f"A imagem excede o limite de {settings.MAX_AVATAR_MB}MB.")

        avatars_dir = Path(settings.UPLOAD_DIR) / "avatars"
        avatars_dir.mkdir(parents=True, exist_ok=True)
        self._delete_avatar_file(user)

        filename = f"{user.id}_{uuid.uuid4().hex[:8]}{ext}"
        (avatars_dir / filename).write_bytes(content)

        user.avatar_url = f"/uploads/avatars/{filename}"
        self.db.flush()
        self.db.refresh(user)
        return user

    def remove_avatar(self, user: User) -> User:
        self._delete_avatar_file(user)
        user.avatar_url = None
        self.db.flush()
        self.db.refresh(user)
        return user

    def _delete_avatar_file(self, user: User) -> None:
        if not user.avatar_url:
            return
        old_path = Path(settings.UPLOAD_DIR) / user.avatar_url.removeprefix("/uploads/")
        old_path.unlink(missing_ok=True)
