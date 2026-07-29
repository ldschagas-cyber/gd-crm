"""Repositório de snippets."""
from sqlalchemy import or_

from app.models.snippet import Snippet
from app.repositories.base import BaseRepository


class SnippetRepository(BaseRepository[Snippet]):
    model = Snippet

    def search_filter(self, termo: str):
        like = f"%{termo}%"
        return or_(Snippet.nome.ilike(like), Snippet.atalho.ilike(like))

    def get_by_atalho(self, atalho: str) -> Snippet | None:
        return self.db.execute(self._base_query().where(Snippet.atalho == atalho)).scalar_one_or_none()
