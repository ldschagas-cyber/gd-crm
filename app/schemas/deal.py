"""DTOs de negócio."""
from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.deal import DealStatus, DealTipo
from app.schemas.common import ORMModel


class DealItemCreate(BaseModel):
    produto_id: UUID
    descricao: str | None = Field(default=None, max_length=200)
    # Preço mensal para produto RECORRENTE (mesma convenção de
    # PropostaItem.preco_proposto/ContratoItem.preco); valor total para PONTUAL.
    preco: float = Field(ge=0)
    quantidade: int = Field(default=1, ge=1)


class DealItemRead(ORMModel):
    id: UUID
    produto_id: UUID
    descricao: str
    preco: float
    quantidade: int


class DealCreate(BaseModel):
    nome: str = Field(min_length=1, max_length=255)
    company_id: UUID
    contact_id: UUID | None = None
    responsavel_id: UUID
    pipeline_id: UUID
    stage_id: UUID
    # `valor_previsto` é o fallback manual usado quando o negócio não tem linha de
    # produto (`itens` abaixo) — ver DealService._aplicar_itens/AssinaturaService.
    # Com itens, valor_previsto é sempre recalculado como a soma deles.
    valor_previsto: float | None = None
    probabilidade: int | None = Field(default=None, ge=0, le=100)
    data_prev_fechamento: date | None = None
    itens: list[DealItemCreate] | None = None
    # Sem `origem` aqui de propósito — o negócio herda a origem da empresa na criação
    # (ver DealService.create), não é escolhida manualmente.
    # Customer Success (ver docs/PLANO_CUSTOMER_SUCCESS.md) — default novo_negocio pra
    # todo fluxo comum de Vendas; o drawer de Clientes envia expansao explicitamente.
    tipo: DealTipo = DealTipo.NOVO_NEGOCIO


class DealUpdate(BaseModel):
    nome: str | None = None
    contact_id: UUID | None = None
    responsavel_id: UUID | None = None
    valor_previsto: float | None = None
    probabilidade: int | None = Field(default=None, ge=0, le=100)
    data_prev_fechamento: date | None = None
    # None = não mexe nos itens existentes; [] = remove todos (fica só no fallback
    # valor_previsto digitado); lista preenchida = substitui por completo.
    itens: list[DealItemCreate] | None = None
    # Previsão Comercial (ver docs/PLANO_PREVISAO_COMERCIAL.md) — o vendedor confirma que
    # fecha este mês. Campo isolado de propósito: dá pra togglar sem reenviar o resto do
    # formulário (PUT já ignora campos não enviados via exclude_unset).
    commit: bool | None = None


class DealStageMove(BaseModel):
    stage_id: UUID


class DealClose(BaseModel):
    status: DealStatus
    motivo_perda: str | None = None


class DealRead(ORMModel):
    id: UUID
    nome: str
    company_id: UUID
    contact_id: UUID | None
    responsavel_id: UUID
    pipeline_id: UUID
    stage_id: UUID
    valor_previsto: float | None
    probabilidade: int | None
    data_prev_fechamento: date | None
    origem: str | None
    status: str
    motivo_perda: str | None
    data_fechamento: datetime | None
    commit: bool
    tipo: str
    created_at: datetime
    ultima_interacao: datetime
    itens: list[DealItemRead] = []
