"""DTOs de Produto (RF-PROD)."""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.models.product import ProdutoTipo
from app.schemas.common import ORMModel


class ProdutoBase(BaseModel):
    nome: str = Field(min_length=1, max_length=160)
    descricao: str | None = None
    tipo: ProdutoTipo = ProdutoTipo.RECORRENTE
    preco_tabela: float = Field(ge=0)
    preco_minimo: float = Field(default=0, ge=0)
    ativo: bool = True

    @model_validator(mode="after")
    def piso_nao_maior_que_tabela(self):
        if self.preco_minimo > self.preco_tabela:
            raise ValueError("Preço mínimo (piso) não pode ser maior que o preço de tabela")
        return self


class ProdutoCreate(ProdutoBase):
    pass


class ProdutoUpdate(BaseModel):
    nome: str | None = Field(default=None, min_length=1, max_length=160)
    descricao: str | None = None
    tipo: ProdutoTipo | None = None
    preco_tabela: float | None = Field(default=None, ge=0)
    preco_minimo: float | None = Field(default=None, ge=0)
    ativo: bool | None = None


class ProdutoRead(ORMModel):
    id: UUID
    nome: str
    descricao: str | None
    tipo: str
    preco_tabela: float
    preco_minimo: float
    ativo: bool
    created_at: datetime
    updated_at: datetime


class ProdutoPrecoHistRead(ORMModel):
    id: UUID
    produto_id: UUID
    preco_anterior: float | None
    preco_novo: float
    usuario_id: UUID | None
    created_at: datetime
