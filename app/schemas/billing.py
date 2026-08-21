"""DTOs de Cobrança, Categoria financeira e Faturamento (RF-FAT/RF-CAR/RF-CAT)."""
from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.finance_category import CategoriaTipo
from app.schemas.common import ORMModel


class CobrancaRead(ORMModel):
    id: UUID
    contrato_id: UUID | None
    company_id: UUID
    categoria_id: UUID | None
    competencia: str
    descricao: str
    tipo: str
    valor: float
    vencimento: date
    status: str
    valor_recebido: float
    data_baixa: date | None
    nf_solicitada_em: datetime | None
    nf_numero: str | None
    created_at: datetime


class CobrancaPontualCreate(BaseModel):
    company_id: UUID
    categoria_id: UUID | None = None
    descricao: str = Field(min_length=1, max_length=200)
    valor: float = Field(gt=0)
    vencimento: date
    competencia: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}$")


class CategoriaCreate(BaseModel):
    nome: str = Field(min_length=1, max_length=80)
    tipo: CategoriaTipo = CategoriaTipo.RECEITA


class CategoriaRead(ORMModel):
    id: UUID
    nome: str
    tipo: str
    ativo: bool


class FaturamentoGerar(BaseModel):
    competencia: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}$")  # default: mês corrente


class FaturamentoCompetencia(BaseModel):
    competencia: str
    cobrancas: list[CobrancaRead]


class FaturamentoResult(BaseModel):
    competencia: str
    geradas: int
    ja_existentes: int
    valor_total: float
    nf_solicitadas: int
    nf_email_enviado: bool
    nf_aviso: str | None = None  # ex.: "sem mailbox conectada" / "contador não configurado"
