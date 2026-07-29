"""Contexto de requisição: tenant e usuário atuais via ContextVar.

Centraliza o isolamento multi-tenant. O tenant_id é definido a partir do
claim do JWT (nunca do corpo da requisição) e consumido pelo BaseRepository.
"""
from contextvars import ContextVar
from uuid import UUID

_current_tenant_id: ContextVar[UUID | None] = ContextVar("current_tenant_id", default=None)
_current_user_id: ContextVar[UUID | None] = ContextVar("current_user_id", default=None)


def set_current_tenant(tenant_id: UUID | None) -> None:
    _current_tenant_id.set(tenant_id)


def get_current_tenant() -> UUID | None:
    return _current_tenant_id.get()


def set_current_user(user_id: UUID | None) -> None:
    _current_user_id.set(user_id)


def get_current_user_id() -> UUID | None:
    return _current_user_id.get()
