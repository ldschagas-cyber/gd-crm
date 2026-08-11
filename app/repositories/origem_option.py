"""Repositório de OrigemOption."""
from sqlalchemy import func

from app.models.origem_option import OrigemOption
from app.repositories.base import BaseRepository


class OrigemOptionRepository(BaseRepository[OrigemOption]):
    model = OrigemOption

    def get_by_nome(self, nome: str) -> OrigemOption | None:
        stmt = self._base_query().where(func.lower(OrigemOption.nome) == nome.strip().lower())
        return self.db.execute(stmt).scalar_one_or_none()

    def list_all(self) -> list[OrigemOption]:
        stmt = self._base_query().order_by(OrigemOption.nome)
        return list(self.db.execute(stmt).scalars().all())
