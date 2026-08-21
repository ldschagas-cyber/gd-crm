"""DTOs de Metas de Ligações — meta por mês (semanal e mensal) por vendedor.

Meta vem de CallTarget (por vendedor/mês); realizado = tarefas tipo=ligacao
concluídas. O bloco semanal só faz sentido quando o mês consultado é o corrente
(a "semana atual" pertence ao mês corrente). Ver MetasLigacoesService."""
from uuid import UUID

from pydantic import BaseModel, Field


class CallTargetInput(BaseModel):
    user_id: UUID
    meta_semanal: int | None = Field(default=None, ge=0)
    meta_mensal: int | None = Field(default=None, ge=0)


class MetaLigacoesRow(BaseModel):
    user_id: UUID
    nome: str
    perfil: str
    ligacoes_semana: int  # da semana corrente; só relevante se mes_corrente
    meta_semanal: int | None
    ligacoes_mes: int  # do mês consultado
    meta_mensal: int | None


class MetaLigacoesResponse(BaseModel):
    periodo: str  # AAAA-MM consultado
    mes_corrente: bool  # se o mês consultado é o mês de hoje (habilita o bloco semanal)
    rows: list[MetaLigacoesRow]
