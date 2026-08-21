"""DTOs de Proposta (RF-PROP) — captura de desconto, sem governança."""
from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.proposal import PropostaStatus
from app.schemas.common import ORMModel


class PropostaItemCreate(BaseModel):
    produto_id: UUID
    descricao: str | None = Field(default=None, max_length=200)
    # O cliente informa o preço proposto (ou o desconto); o desconto é sempre derivado
    # no service a partir do snapshot do preço de tabela (RN-F09). preco_tabela nunca
    # vem do cliente — é lido do produto no momento da criação.
    preco_proposto: float = Field(ge=0)
    quantidade: int = Field(default=1, ge=1)


class PropostaItemRead(ORMModel):
    id: UUID
    produto_id: UUID
    descricao: str
    preco_tabela: float
    preco_proposto: float
    desconto_pct: float
    quantidade: int


class PropostaCreate(BaseModel):
    company_id: UUID
    deal_id: UUID | None = None
    vendedor_id: UUID | None = None
    validade: date | None = None
    observacao: str | None = None
    itens: list[PropostaItemCreate] = Field(min_length=1)


class PropostaUpdate(BaseModel):
    vendedor_id: UUID | None = None
    validade: date | None = None
    observacao: str | None = None
    itens: list[PropostaItemCreate] | None = None


class PropostaStatusUpdate(BaseModel):
    status: PropostaStatus


class PropostaRead(ORMModel):
    id: UUID
    numero: str
    company_id: UUID
    deal_id: UUID | None
    vendedor_id: UUID | None
    versao: int
    status: str
    validade: date | None
    observacao: str | None
    valor_tabela_total: float
    valor_proposto_total: float
    desconto_pct_total: float
    contrato_id: UUID | None
    created_at: datetime
    updated_at: datetime
    itens: list[PropostaItemRead] = []
