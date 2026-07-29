"""Funções de segurança: hashing de senha e emissão/validação de JWT."""
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ACCESS = "access"
REFRESH = "refresh"
RESET = "reset"
MS_OAUTH_STATE = "ms_oauth_state"


def hash_password(senha: str) -> str:
    return pwd_context.hash(senha)


def verify_password(senha: str, senha_hash: str) -> bool:
    return pwd_context.verify(senha, senha_hash)


def _create_token(subject: UUID, tenant_id: UUID, perfil: str, token_type: str, expires: timedelta) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "tenant_id": str(tenant_id),
        "perfil": perfil,
        "type": token_type,
        "iat": now,
        "exp": now + expires,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_access_token(user_id: UUID, tenant_id: UUID, perfil: str) -> str:
    return _create_token(user_id, tenant_id, perfil, ACCESS,
                         timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))


def create_refresh_token(user_id: UUID, tenant_id: UUID, perfil: str) -> str:
    return _create_token(user_id, tenant_id, perfil, REFRESH,
                         timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))


def create_reset_token(user_id: UUID, tenant_id: UUID, perfil: str) -> str:
    return _create_token(user_id, tenant_id, perfil, RESET,
                         timedelta(minutes=settings.PASSWORD_RESET_EXPIRE_MINUTES))


def create_ms_oauth_state(user_id: UUID, tenant_id: UUID, tipo: str) -> str:
    """Carrega quem está conectando o quê através do redirect do Microsoft Entra.

    O callback OAuth chega como um GET puro do navegador (sem Authorization
    header), então não dá pra usar `get_current_user` — este token substitui
    a sessão nesse trecho, com vida curta e sem uso além dessa troca.
    """
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": str(user_id), "tenant_id": str(tenant_id), "tipo": tipo,
        "type": MS_OAUTH_STATE, "iat": now, "exp": now + timedelta(minutes=10),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    """Decodifica e valida assinatura/expiração. Lança jwt.PyJWTError em falha."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
