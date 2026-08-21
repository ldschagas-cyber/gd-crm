"""DTOs de Contrato (RF-CONTR). Nesta fase o contrato nasce do aceite da proposta;
não há CRUD completo de tela — só leitura e ativação."""
from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel

from app.schemas.common import ORMModel


class ContratoItemRead(ORMModel):
    id: UUID
    produto_id: UUID
    descricao: str
    preco: float
    quantidade: int


class ContratoRead(ORMModel):
    id: UUID
    numero: str
    proposta_id: UUID | None
    company_id: UUID
    vendedor_id: UUID | None
    status: str
    data_inicio: date
    vigencia_meses: int | None
    valor_mensal: float
    reajuste_indice: str | None
    reajuste_mes: int | None
    assinatura_id: UUID | None
    created_at: datetime
    updated_at: datetime
    itens: list[ContratoItemRead] = []


class ContratoAtivar(BaseModel):
    data_inicio: date | None = None
    vigencia_meses: int | None = None
    reajuste_indice: str | None = None
    reajuste_mes: int | None = None
