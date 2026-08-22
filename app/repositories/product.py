"""Repositórios de Produto e histórico de preço."""
from uuid import UUID

from sqlalchemy import or_

from app.models.product import Produto, ProdutoPrecoHist
from app.repositories.base import BaseRepository


class ProdutoRepository(BaseRepository[Produto]):
    model = Produto

    def search_filter(self, termo: str):
        like = f"%{termo}%"
        return or_(Produto.nome.ilike(like), Produto.descricao.ilike(like))


class ProdutoPrecoHistRepository(BaseRepository[ProdutoPrecoHist]):
    model = ProdutoPrecoHist

    def list_by_produto(self, produto_id: UUID) -> list[ProdutoPrecoHist]:
        stmt = self._base_query().where(ProdutoPrecoHist.produto_id == produto_id).order_by(
            ProdutoPrecoHist.created_at.desc()
        )
        return list(self.db.execute(stmt).scalars().all())
