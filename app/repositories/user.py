"""Repositório de usuários."""
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    def search_filter(self, termo: str):
        like = f"%{termo}%"
        return or_(User.nome.ilike(like), User.email.ilike(like))

    def get_by_email_global(self, db: Session, email: str) -> User | None:
        """Busca por e-mail sem filtro de tenant (usado no login)."""
        return db.execute(select(User).where(User.email == email)).scalar_one_or_none()

    def get_by_email(self, email: str) -> User | None:
        return self.db.execute(self._base_query().where(User.email == email)).scalar_one_or_none()
