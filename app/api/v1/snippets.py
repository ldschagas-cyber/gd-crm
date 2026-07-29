"""Rotas de snippets (§9.6)."""
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.common import Page, PageParams
from app.schemas.snippet import SnippetCreate, SnippetRead, SnippetUpdate
from app.services.snippet import SnippetService

router = APIRouter(prefix="/snippets", tags=["Snippets"])


@router.get("", response_model=Page[SnippetRead])
def list_snippets(params: PageParams = Depends(), busca: str | None = None,
                   _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    items, total = SnippetService(db).list(params, busca)
    return Page(items=items, total=total, page=params.page, size=params.size)


@router.post("", response_model=SnippetRead, status_code=status.HTTP_201_CREATED)
def create_snippet(data: SnippetCreate, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return SnippetService(db).create(data)


@router.get("/{snippet_id}", response_model=SnippetRead)
def get_snippet(snippet_id: UUID, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return SnippetService(db).get(snippet_id)


@router.put("/{snippet_id}", response_model=SnippetRead)
def update_snippet(snippet_id: UUID, data: SnippetUpdate, _: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    return SnippetService(db).update(snippet_id, data)


@router.delete("/{snippet_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_snippet(snippet_id: UUID, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    SnippetService(db).delete(snippet_id)
