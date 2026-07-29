"""Criptografia em repouso para tokens OAuth (UserIntegration.access_token_enc/refresh_token_enc)."""
from functools import lru_cache

from cryptography.fernet import Fernet

from app.core.config import settings


@lru_cache
def _fernet() -> Fernet:
    if not settings.TOKEN_ENCRYPTION_KEY:
        raise RuntimeError("TOKEN_ENCRYPTION_KEY não configurada — não é possível gravar tokens OAuth.")
    return Fernet(settings.TOKEN_ENCRYPTION_KEY.encode())


def encrypt_token(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def decrypt_token(value: str) -> str:
    return _fernet().decrypt(value.encode()).decode()
