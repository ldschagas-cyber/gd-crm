"""Dependências FastAPI: sessão, usuário autenticado, tenant e autorização."""
from collections.abc import Callable
from uuid import UUID

import jwt
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core import security
from app.core.context import set_current_tenant, set_current_user
from app.core.database import get_db
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.models.user import User, UserStatus

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Valida o JWT, carrega o usuário e fixa o contexto de tenant/usuário.

    O tenant é sempre derivado do token assinado, nunca do corpo da requisição.

    Precisa ser `async def`: FastAPI despacha dependências `def` síncronas para
    threads do threadpool via `contextvars.copy_context()`, e mutações feitas
    dentro dessa cópia (como `set_current_tenant`) não se propagam de volta ao
    contexto ambiente da requisição nem para as próximas chamadas síncronas
    (endpoint, outras dependências) — cada uma roda numa cópia própria e
    independente. Como `async def` executa direto na task do event loop, a
    mutação do ContextVar fica visível para tudo que vier depois na mesma
    requisição, inclusive path operations `def` síncronas.
    """
    try:
        payload = security.decode_token(token)
        if payload.get("type") != security.ACCESS:
            raise UnauthorizedError("Token inválido")
        user_id = UUID(payload["sub"])
        tenant_id = UUID(payload["tenant_id"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise UnauthorizedError("Não autenticado")

    # Fixa o tenant ANTES de consultar, garantindo isolamento já na carga do usuário.
    set_current_tenant(tenant_id)
    set_current_user(user_id)

    user = db.get(User, user_id)
    if user is None or user.tenant_id != tenant_id:
        raise UnauthorizedError("Usuário não encontrado")
    if user.status != UserStatus.ATIVO:
        raise ForbiddenError("Usuário inativo")
    return user


def require_roles(*perfis: str) -> Callable[[User], User]:
    """Fábrica de dependência de autorização por perfil."""
    def _checker(user: User = Depends(get_current_user)) -> User:
        if user.perfil not in perfis:
            raise ForbiddenError("Acesso negado para o seu perfil")
        return user
    return _checker
