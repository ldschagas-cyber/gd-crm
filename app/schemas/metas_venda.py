"""DTOs de Metas de Venda — quantidade e valor por vendedor e por equipe, por mês.

Meta vem de SalesTarget (por vendedor/mês); realizado é lido ao vivo dos negócios
ganhos. A meta da equipe é a soma dos vendedores. Ver docs/PLANO_METAS_VENDA.md."""
from uuid import UUID

from pydantic import BaseModel, Field

# Status de cada indicador (qtd ou valor) contra a meta: ok >= 100%, atenção >= 70%,
# crítico abaixo. None quando não há meta definida para o vendedor no mês.
Status = str  # "ok" | "atencao" | "critico"


class SalesTargetInput(BaseModel):
    user_id: UUID
    meta_qtd: int | None = Field(default=None, ge=0)
    meta_valor: float | None = Field(default=None, ge=0)


class VendedorMetaRow(BaseModel):
    user_id: UUID
    nome: str
    team_id: UUID | None
    meta_qtd: int | None
    meta_valor: float | None
    realizado_qtd: int
    realizado_valor: float
    status_qtd: Status | None
    status_valor: Status | None


class EquipeResumo(BaseModel):
    team_id: UUID | None  # None = bucket "Sem equipe"
    nome: str
    gestor_nome: str | None
    meta_qtd: int
    meta_valor: float
    realizado_qtd: int
    realizado_valor: float
    status_qtd: Status
    status_valor: Status
    vendedores: list[VendedorMetaRow]


class MetasVendaResumo(BaseModel):
    periodo: str  # AAAA-MM
    equipes: list[EquipeResumo]
    total_meta_qtd: int
    total_meta_valor: float
    total_realizado_qtd: int
    total_realizado_valor: float
