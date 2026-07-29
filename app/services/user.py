"""Serviço de usuários."""
from uuid import UUID

from sqlalchemy.orm import Session

from app.core import security
from app.core.exceptions import ConflictError, NotFoundError
from app.models.user import User
from app.repositories.user import UserRepository
from app.schemas.common import PageParams
from app.schemas.user import UserCreate, UserStatusUpdate, UserUpdate


class UserService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = UserRepository(db)

    def list(self, params: PageParams, busca: str | None = None,
             perfil: str | None = None) -> tuple[list[User], int]:
        filters = []
        if busca:
            filters.append(self.repo.search_filter(busca))
        if perfil:
            filters.append(User.perfil == perfil)
        return self.repo.list(*filters, offset=params.offset, limit=params.size, order_by=User.nome)

    def get(self, user_id: UUID) -> User:
        user = self.repo.get(user_id)
        if user is None:
            raise NotFoundError("Usuário não encontrado")
        return user

    def create(self, data: UserCreate) -> User:
        if self.repo.get_by_email(data.email):
            raise ConflictError("E-mail já cadastrado neste tenant")
        user = User(
            nome=data.nome,
            email=data.email,
            senha_hash=security.hash_password(data.senha),
            telefone=data.telefone,
            cargo=data.cargo,
            perfil=data.perfil.value,
        )
        return self.repo.add(user)

    def update(self, user_id: UUID, data: UserUpdate) -> User:
        user = self.get(user_id)
        payload = data.model_dump(exclude_unset=True)
        if "perfil" in payload and payload["perfil"] is not None:
            payload["perfil"] = payload["perfil"].value
        for field, value in payload.items():
            setattr(user, field, value)
        return self.repo.save(user)

    def set_status(self, user_id: UUID, data: UserStatusUpdate) -> User:
        user = self.get(user_id)
        user.status = data.status.value
        return self.repo.save(user)
