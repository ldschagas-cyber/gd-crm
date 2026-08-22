"""ProdutoService — catálogo com histórico de preço (RF-PROD)."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.context import get_current_tenant, get_current_user_id
from app.core.exceptions import ConflictError, NotFoundError
from app.core.money import dec, money
from app.models.contract import ContratoItem
from app.models.product import Produto, ProdutoPrecoHist
from app.models.proposal import PropostaItem
from app.repositories.product import ProdutoPrecoHistRepository, ProdutoRepository
from app.schemas.common import PageParams
from app.schemas.product import ProdutoCreate, ProdutoUpdate


class ProdutoService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ProdutoRepository(db)
        self.hist = ProdutoPrecoHistRepository(db)

    def list(self, params: PageParams, busca: str | None = None,
             ativo: bool | None = None) -> tuple[list[Produto], int]:
        filters = []
        if busca:
            filters.append(self.repo.search_filter(busca))
        if ativo is not None:
            filters.append(Produto.ativo == ativo)
        return self.repo.list(*filters, offset=params.offset, limit=params.size, order_by=Produto.nome)

    def get(self, produto_id: UUID) -> Produto:
        produto = self.repo.get(produto_id)
        if produto is None:
            raise NotFoundError("Produto não encontrado")
        return produto

    def create(self, data: ProdutoCreate) -> Produto:
        produto = Produto(
            nome=data.nome, descricao=data.descricao, tipo=data.tipo.value,
            preco_tabela=money(data.preco_tabela), preco_minimo=money(data.preco_minimo),
            ativo=data.ativo,
        )
        return self.repo.add(produto)

    def update(self, produto_id: UUID, data: ProdutoUpdate) -> Produto:
        produto = self.get(produto_id)
        payload = data.model_dump(exclude_unset=True)
        # Alteração de preço de tabela é registrada no histórico (RF-PROD-05) e NÃO
        # retroage (o snapshot já foi gravado nos itens existentes, RN-F13).
        if "preco_tabela" in payload and payload["preco_tabela"] is not None:
            novo = money(payload["preco_tabela"])
            if novo != dec(produto.preco_tabela):
                self.hist.add(ProdutoPrecoHist(
                    produto_id=produto.id, preco_anterior=produto.preco_tabela,
                    preco_novo=novo, usuario_id=get_current_user_id(),
                ))
            payload["preco_tabela"] = novo
        if "preco_minimo" in payload and payload["preco_minimo"] is not None:
            payload["preco_minimo"] = money(payload["preco_minimo"])
        if "tipo" in payload and payload["tipo"] is not None:
            payload["tipo"] = payload["tipo"].value
        for field, value in payload.items():
            setattr(produto, field, value)
        return self.repo.save(produto)

    def historico_preco(self, produto_id: UUID) -> list[ProdutoPrecoHist]:
        self.get(produto_id)  # valida existência/tenant
        return self.hist.list_by_produto(produto_id)

    def delete(self, produto_id: UUID) -> None:
        produto = self.get(produto_id)
        tenant_id = get_current_tenant()
        em_proposta = self.db.execute(
            select(PropostaItem.id).where(
                PropostaItem.tenant_id == tenant_id, PropostaItem.produto_id == produto_id
            ).limit(1)
        ).scalar_one_or_none()
        em_contrato = self.db.execute(
            select(ContratoItem.id).where(
                ContratoItem.tenant_id == tenant_id, ContratoItem.produto_id == produto_id
            ).limit(1)
        ).scalar_one_or_none()
        if em_proposta is not None or em_contrato is not None:
            raise ConflictError(
                "Produto já usado em proposta ou contrato — desative em vez de excluir."
            )
        for h in self.hist.list_by_produto(produto_id):
            self.hist.delete(h)
        self.repo.delete(produto)
