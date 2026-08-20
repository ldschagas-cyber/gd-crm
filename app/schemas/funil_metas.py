"""DTOs de Metas do Funil — controle de mudança de fase por percentual (Anexo 1).
Ver docs/PLANO_METAS_FUNIL.md."""
from pydantic import BaseModel, Field

# Ordem fixa das etapas — mesma do Anexo 1. "pesquisadas" não entra na config (é a
# base, editada separadamente como `empresas_pesquisadas_meta`) nem tem
# `pct_etapa_anterior` (não tem etapa anterior).
ETAPAS_CHAVES = ["decisores", "contatos", "reunioes", "diagnosticos", "propostas", "fechados"]

DEFAULT_PCTS = {
    "decisores": 33, "contatos": 50, "reunioes": 60,
    "diagnosticos": 67, "propostas": 75, "fechados": 67,
}


class FunilEtapaMeta(BaseModel):
    chave: str
    pct_etapa_anterior: int = Field(ge=0, le=100)


class FunilMetasConfig(BaseModel):
    """Meta absoluta de cada etapa é sempre derivada em cascata a partir de
    `empresas_pesquisadas_meta` e dos percentuais abaixo — nunca gravada como número
    solto, pra evitar os dois ficarem inconsistentes entre si (ver §5 do plano)."""
    empresas_pesquisadas_meta: int = Field(default=300, ge=1)
    etapas: list[FunilEtapaMeta] = Field(
        default_factory=lambda: [FunilEtapaMeta(chave=c, pct_etapa_anterior=DEFAULT_PCTS[c]) for c in ETAPAS_CHAVES]
    )


class FunilEtapaResumo(BaseModel):
    chave: str
    nome: str
    meta: int
    real: int
    pct_meta_etapa_anterior: float | None  # None só na etapa 0 (empresas pesquisadas)
    pct_real_etapa_anterior: float | None
    diferenca_pp: float | None  # pct_real - pct_meta, negativo = abaixo do esperado
    status: str  # "ok" | "atencao" | "critico"


class FunilMetasResumo(BaseModel):
    modo: str  # "coorte" | "atividade"
    periodo: str  # AAAA-MM (visão mensal) ou AAAA (visão anual agregada)
    etapas: list[FunilEtapaResumo]
    # Ponte com Previsão Comercial (ver docs/PLANO_PREVISAO_COMERCIAL.md §3) — soma de
    # valor_previsto em R$ pra a etapa "Propostas enviadas" (negócios abertos na(s) etapa(s)
    # marcada(s) marco_funil="proposta") e pra "Clientes fechados" (negócios ganho no período).
    # None quando o tenant não tem etapa de proposta marcada — mesmo fallback que o resto do
    # Anexo 1 já tem pra marco_funil ausente.
    propostas_valor_aberto: float | None = None
    fechados_valor_realizado: float | None = None
