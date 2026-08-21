"""Rotas de Produtos (RF-PROD)."""
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.common import Page, PageParams
from app.schemas.product import ProdutoCreate, ProdutoPrecoHistRead, ProdutoRead, ProdutoUpdate
from app.services.product import ProdutoService

router = APIRouter(prefix="/produtos", tags=["Financeiro — Produtos"])


@router.get("", response_model=Page[ProdutoRead])
def list_produtos(params: PageParams = Depends(), busca: str | None = None, ativo: bool | None = None,
                  _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    items, total = ProdutoService(db).list(params, busca, ativo)
    return Page(items=items, total=total, page=params.page, size=params.size)


@router.post("", response_model=ProdutoRead, status_code=status.HTTP_201_CREATED)
def create_produto(data: ProdutoCreate, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ProdutoService(db).create(data)


@router.get("/{produto_id}", response_model=ProdutoRead)
def get_produto(produto_id: UUID, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ProdutoService(db).get(produto_id)


@router.put("/{produto_id}", response_model=ProdutoRead)
def update_produto(produto_id: UUID, data: ProdutoUpdate, _: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    return ProdutoService(db).update(produto_id, data)


@router.get("/{produto_id}/historico-preco", response_model=list[ProdutoPrecoHistRead])
def historico_preco(produto_id: UUID, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ProdutoService(db).historico_preco(produto_id)
