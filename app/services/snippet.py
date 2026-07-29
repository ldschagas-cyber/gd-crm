"""Serviço de snippets."""
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.context import get_current_user_id
from app.core.exceptions import ConflictError, NotFoundError
from app.models.snippet import Snippet
from app.repositories.snippet import SnippetRepository
from app.schemas.common import PageParams
from app.schemas.snippet import SnippetCreate, SnippetUpdate


class SnippetService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = SnippetRepository(db)

    def list(self, params: PageParams, busca: str | None = None) -> tuple[list[Snippet], int]:
        filters = []
        if busca:
            filters.append(self.repo.search_filter(busca))
        return self.repo.list(*filters, offset=params.offset, limit=params.size, order_by=Snippet.nome)

    def get(self, snippet_id: UUID) -> Snippet:
        snippet = self.repo.get(snippet_id)
        if snippet is None:
            raise NotFoundError("Snippet não encontrado")
        return snippet

    def create(self, data: SnippetCreate) -> Snippet:
        if self.repo.get_by_atalho(data.atalho):
            raise ConflictError(f'Esse atalho já é usado por outro snippet: "#{data.atalho}"')
        snippet = Snippet(nome=data.nome, atalho=data.atalho, conteudo=data.conteudo,
                          created_by=get_current_user_id())
        return self.repo.add(snippet)

    def update(self, snippet_id: UUID, data: SnippetUpdate) -> Snippet:
        snippet = self.get(snippet_id)
        payload = data.model_dump(exclude_unset=True)
        if "atalho" in payload and payload["atalho"] is not None:
            existing = self.repo.get_by_atalho(payload["atalho"])
            if existing and existing.id != snippet_id:
                raise ConflictError(f'Esse atalho já é usado por outro snippet: "#{payload["atalho"]}"')
        for field, value in payload.items():
            setattr(snippet, field, value)
        return self.repo.save(snippet)

    def delete(self, snippet_id: UUID) -> None:
        snippet = self.get(snippet_id)
        self.repo.delete(snippet)
