"""Serviço de autenticação e gestão de sessão (JWT)."""
from datetime import datetime, timezone

import jwt
from sqlalchemy.orm import Session

from app.core import security
from app.core.exceptions import UnauthorizedError
from app.models.user import User, UserStatus
from app.repositories.user import UserRepository
from app.schemas.auth import LoginRequest, ResetPasswordRequest, TokenResponse


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.users = UserRepository(db)

    def login(self, data: LoginRequest) -> TokenResponse:
        user = self.users.get_by_email_global(self.db, data.email)
        if user is None or not security.verify_password(data.senha, user.senha_hash):
            raise UnauthorizedError("E-mail ou senha inválidos")
        if user.status != UserStatus.ATIVO.value:
            raise UnauthorizedError("Usuário inativo")
        user.ultimo_acesso = datetime.now(timezone.utc)
        self.db.flush()
        return self._tokens(user)

    def refresh(self, refresh_token: str) -> TokenResponse:
        try:
            payload = security.decode_token(refresh_token)
            if payload.get("type") != security.REFRESH:
                raise UnauthorizedError("Token inválido")
        except jwt.PyJWTError:
            raise UnauthorizedError("Refresh token inválido ou expirado")
        user = self.db.get(User, payload["sub"])
        if user is None:
            raise UnauthorizedError("Usuário não encontrado")
        return self._tokens(user)

    def reset_password(self, data: ResetPasswordRequest) -> None:
        try:
            payload = security.decode_token(data.token)
            if payload.get("type") != security.RESET:
                raise UnauthorizedError("Token inválido")
        except jwt.PyJWTError:
            raise UnauthorizedError("Token de redefinição inválido ou expirado")
        user = self.db.get(User, payload["sub"])
        if user is None:
            raise UnauthorizedError("Usuário não encontrado")
        user.senha_hash = security.hash_password(data.nova_senha)
        self.db.flush()

    def generate_reset_token(self, email: str) -> str | None:
        """Gera token de redefinição. Retorna None se o e-mail não existir
        (a rota responde 202 de qualquer forma, para não revelar existência)."""
        user = self.users.get_by_email_global(self.db, email)
        if user is None:
            return None
        return security.create_reset_token(user.id, user.tenant_id, user.perfil)

    @staticmethod
    def _tokens(user: User) -> TokenResponse:
        return TokenResponse(
            access_token=security.create_access_token(user.id, user.tenant_id, user.perfil),
            refresh_token=security.create_refresh_token(user.id, user.tenant_id, user.perfil),
        )
