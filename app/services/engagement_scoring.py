"""Motor de Score de Engajamento — segundo componente do Lead Score da Central de
Leads, somado ao Score ICP (app/services/icp_scoring.py) pra formar o score final
mostrado no funil (60% ICP + 40% engajamento, pesos configuráveis por tenant). Ver
docs/PLANO_CENTRAL_DE_LEADS.md §2.

Ao contrário do Score ICP (perfil da empresa — estático), o Score de Engajamento é
dinâmico: soma pontos por interação registrada na timeline e por etapas de cadência
concluídas, com decaimento por semana de inatividade — reflete se o lead está esfriando.
Mesmo espírito de app/services/icp_scoring.py: funções puras, sem I/O, fáceis de testar
e de reaproveitar tanto no cálculo persistido quanto num preview client-side.
"""
from dataclasses import dataclass, field

DEFAULT_ENGAGEMENT_RULES = {
    # pontos por evento de timeline dentro da janela considerada (chaves = TimelineType)
    "eventos": {
        "email": 8,
        "ligacao": 18,
        "reuniao": 30,
        "nota": 4,
        "tarefa": 5,
    },
    "etapa_cadencia_concluida": 5,
    "decaimento_por_semana_sem_interacao": 10,
    "quente_a_partir_de": 70,
    "morno_a_partir_de": 40,
}

# Eventos de timeline mais antigos que isso não pontuam mais o engajamento — mas
# continuam contando normalmente pra "última interação" (Company.ultima_interacao),
# que é um cálculo à parte e nunca "esquece" o evento mais recente.
JANELA_DIAS = 60


@dataclass
class EngagementBreakdownItem:
    criterio: str
    valor: str
    pontos: int


@dataclass
class EngagementResult:
    score: int
    breakdown: list[EngagementBreakdownItem] = field(default_factory=list)


def calcular_engajamento(
    *,
    eventos_tipos: list[str],
    etapas_cadencia_concluidas: int = 0,
    dias_desde_ultima_interacao: int | None,
    rules: dict,
) -> EngagementResult:
    """`eventos_tipos`: os `tipo` de TimelineEvent já filtrados pelo chamador para a
    janela de `JANELA_DIAS`. `etapas_cadencia_concluidas`: quantas etapas da cadência
    ativa (se houver) já foram disparadas. `dias_desde_ultima_interacao`: None se a
    empresa nunca teve nenhuma interação registrada."""
    breakdown: list[EngagementBreakdownItem] = []

    pontos_por_tipo: dict[str, int] = {}
    for tipo in eventos_tipos:
        pts = rules["eventos"].get(tipo, 0)
        if pts:
            pontos_por_tipo[tipo] = pontos_por_tipo.get(tipo, 0) + pts
    for tipo, pts in pontos_por_tipo.items():
        breakdown.append(EngagementBreakdownItem(f"Interações — {tipo}", str(pts), pts))

    pontos_cadencia = etapas_cadencia_concluidas * rules["etapa_cadencia_concluida"]
    if pontos_cadencia:
        breakdown.append(EngagementBreakdownItem(
            "Etapas de cadência concluídas", str(etapas_cadencia_concluidas), pontos_cadencia,
        ))

    bruto = sum(pontos_por_tipo.values()) + pontos_cadencia

    decaimento = 0
    if dias_desde_ultima_interacao is not None and dias_desde_ultima_interacao > 0:
        semanas = dias_desde_ultima_interacao // 7
        decaimento = semanas * rules["decaimento_por_semana_sem_interacao"]
        if decaimento:
            breakdown.append(EngagementBreakdownItem(
                "Decaimento por inatividade", f"{semanas} semana(s) sem interação", -decaimento,
            ))

    score = max(0, min(100, bruto - decaimento))
    return EngagementResult(score=score, breakdown=breakdown)


def temperatura(lead_score: int, rules: dict) -> str:
    """'quente' / 'morno' / 'frio' — só rótulo de exibição, não influencia estágio
    algum: MQL/SQL continuam sempre transição manual mesmo com lead 'quente'."""
    if lead_score >= rules["quente_a_partir_de"]:
        return "quente"
    if lead_score >= rules["morno_a_partir_de"]:
        return "morno"
    return "frio"
