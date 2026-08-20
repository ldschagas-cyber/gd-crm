"""DTOs de Metas de Ligações — progresso por vendedor na semana e no mês correntes.

Realizado = tarefas tipo=ligacao concluídas por vendedor (mesma fonte do dashboard
do vendedor). Meta é fixa por semana/mês (colunas em User). Ver MetasLigacoesService."""
from uuid import UUID

from pydantic import BaseModel


class MetaLigacoesRow(BaseModel):
    user_id: UUID
    nome: str
    ligacoes_semana: int
    meta_semanal: int | None
    ligacoes_mes: int
    meta_mensal: int | None


class MetaLigacoesResponse(BaseModel):
    rows: list[MetaLigacoesRow]
