"""Motor de Health Score — nota de saúde (0-100) de cada cliente no Customer Success.

Mesmo espírito de app/services/icp_scoring.py e app/services/engagement_scoring.py:
funções puras, sem I/O, breakdown auditável em vez de número opaco. Composto de quatro
pilares (pesos configuráveis por tenant, ver docs/PLANO_CUSTOMER_SUCCESS.md §3):

- Engajamento (30%) — reaproveita calcular_engajamento (mesma fórmula da Central de
  Leads), lido sobre a timeline da empresa já cliente.
- Uso/adoção (25%) e Satisfação (20%) — vêm do check-in mais recente do CSM
  (TimelineType.CS_CHECKIN). Dado manual de propósito: o Argos é a ferramenta de vendas
  do tenant, não o produto que ele vende ao cliente final, então não existe hoje uma
  fonte automática de "uso real" (ver plano, decisão 5).
- Financeiro (25%) — status da Assinatura (pausada = sinal de inadimplência/negociação)
  e proximidade da renovação sem contato recente.
"""
from dataclasses import dataclass, field

from app.services.engagement_scoring import DEFAULT_ENGAGEMENT_RULES, calcular_engajamento

DEFAULT_HEALTH_RULES = {
    "peso_engajamento": 30,
    "peso_uso": 25,
    "peso_satisfacao": 20,
    "peso_financeiro": 25,
    "saudavel_a_partir_de": 70,
    "atencao_a_partir_de": 40,
    # Sem check-in nunca registrado, uso/satisfação partem daqui (neutro) em vez de
    # zero — não faz sentido punir um cliente recém-implantado por ainda não ter tido
    # um check-in, mas a ausência de dado fica visível via `precisa_checkin` no resultado.
    "uso_padrao_sem_checkin": 50,
    "satisfacao_padrao_sem_checkin": 50,
    "dias_sem_checkin_para_alerta": 21,
    "penalidade_assinatura_pausada": 60,
    "penalidade_renovacao_sem_contato": 30,
    "dias_renovacao_proxima": 30,
    "dias_contato_recente_para_renovacao": 14,
}


@dataclass
class HealthBreakdownItem:
    criterio: str
    valor: str
    pontos: int


@dataclass
class HealthResult:
    score: int
    engajamento: int
    uso: int
    satisfacao: int
    financeiro: int
    precisa_checkin: bool
    breakdown: list[HealthBreakdownItem] = field(default_factory=list)


def _calcular_financeiro(
    *, assinatura_status: str | None, dias_ate_renovacao: int | None,
    dias_desde_ultima_interacao: int | None, rules: dict,
) -> tuple[int, list[HealthBreakdownItem]]:
    breakdown: list[HealthBreakdownItem] = []
    pontos = 100

    if assinatura_status is None:
        # Cliente ainda sem assinatura cadastrada (comum logo após a implantação,
        # antes do financeiro configurar a cobrança) — neutro, não penaliza.
        pontos = 70
        breakdown.append(HealthBreakdownItem("Financeiro", "sem assinatura registrada ainda", 0))
    elif assinatura_status == "pausada":
        pontos -= rules["penalidade_assinatura_pausada"]
        breakdown.append(HealthBreakdownItem(
            "Assinatura pausada", "inadimplência/negociação", -rules["penalidade_assinatura_pausada"],
        ))
    elif assinatura_status == "cancelada":
        pontos = 0
        breakdown.append(HealthBreakdownItem("Assinatura cancelada", "-", -100))

    if dias_ate_renovacao is not None and 0 <= dias_ate_renovacao <= rules["dias_renovacao_proxima"]:
        sem_contato_recente = (
            dias_desde_ultima_interacao is None
            or dias_desde_ultima_interacao > rules["dias_contato_recente_para_renovacao"]
        )
        if sem_contato_recente:
            pontos -= rules["penalidade_renovacao_sem_contato"]
            breakdown.append(HealthBreakdownItem(
                "Renovação próxima sem contato recente", f"em {dias_ate_renovacao}d",
                -rules["penalidade_renovacao_sem_contato"],
            ))

    return max(0, min(100, pontos)), breakdown


def calcular_saude(
    *,
    eventos_tipos: list[str],
    dias_desde_ultima_interacao: int | None,
    uso_percebido: int | None,
    ultima_satisfacao: int | None,
    dias_desde_ultimo_checkin: int | None,
    assinatura_status: str | None,
    dias_ate_renovacao: int | None,
    rules: dict,
    engagement_rules: dict | None = None,
) -> HealthResult:
    eng = calcular_engajamento(
        eventos_tipos=eventos_tipos, etapas_cadencia_concluidas=0,
        dias_desde_ultima_interacao=dias_desde_ultima_interacao,
        rules=engagement_rules or DEFAULT_ENGAGEMENT_RULES,
    )
    breakdown: list[HealthBreakdownItem] = [
        HealthBreakdownItem("Engajamento", f"{eng.score}pt", eng.score),
    ]

    precisa_checkin = (
        dias_desde_ultimo_checkin is None
        or dias_desde_ultimo_checkin >= rules["dias_sem_checkin_para_alerta"]
    )
    uso = uso_percebido if uso_percebido is not None else rules["uso_padrao_sem_checkin"]
    satisfacao = ultima_satisfacao if ultima_satisfacao is not None else rules["satisfacao_padrao_sem_checkin"]
    breakdown.append(HealthBreakdownItem(
        "Uso/adoção", f"{uso}pt" + (" (sem check-in)" if uso_percebido is None else ""), uso,
    ))
    breakdown.append(HealthBreakdownItem(
        "Satisfação", f"{satisfacao}pt" + (" (sem check-in)" if ultima_satisfacao is None else ""), satisfacao,
    ))

    financeiro, financeiro_breakdown = _calcular_financeiro(
        assinatura_status=assinatura_status, dias_ate_renovacao=dias_ate_renovacao,
        dias_desde_ultima_interacao=dias_desde_ultima_interacao, rules=rules,
    )
    breakdown.extend(financeiro_breakdown)

    score = round(
        eng.score * rules["peso_engajamento"] / 100
        + uso * rules["peso_uso"] / 100
        + satisfacao * rules["peso_satisfacao"] / 100
        + financeiro * rules["peso_financeiro"] / 100
    )
    score = max(0, min(100, score))

    return HealthResult(
        score=score, engajamento=eng.score, uso=uso, satisfacao=satisfacao, financeiro=financeiro,
        precisa_checkin=precisa_checkin, breakdown=breakdown,
    )


def faixa(score: int, rules: dict) -> str:
    """'saudavel' / 'atencao' / 'em_risco' — rótulo de exibição."""
    if score >= rules["saudavel_a_partir_de"]:
        return "saudavel"
    if score >= rules["atencao_a_partir_de"]:
        return "atencao"
    return "em_risco"
