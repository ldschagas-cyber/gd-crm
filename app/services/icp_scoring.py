"""Motor de Score ICP — compartilhado entre Pesquisa de Leads (LeadProspect) e
empresas já promovidas (Company, Dossiê Comercial).

Extraído de LeadProspectService (que até aqui era o único consumidor) pra que o
score de uma Company possa ser calculado com exatamente a mesma regra, sem
depender de o registro ter vindo de uma promoção de lead — ver memória
"Score/ICP se perde na promoção do lead": antes, `Company` não tinha `setor`
nem forma de derivar faixa de funcionários, então o score deixava de existir
assim que o lead virava empresa.
"""
from dataclasses import dataclass, field

DEFAULT_ICP_RULES = {
    "setor": {
        "Farma": 40, "Alimentos": 40, "Autopeças": 40, "Etiquetas": 40,
        "Plástico": 30, "Máquinas e Equipamentos": 30, "Química": 30, "Cosmético": 30,
    },
    "setor_fallback": 10,
    "regiao": {"Sudeste": 30, "Sul": 30, "Nordeste": 30, "Norte": 0, "Centro-Oeste": 0},
    "faixa_funcionarios": {
        "1-50": 0, "51-200": 30, "201-500": 30, "501-1.000": 30,
        "1.001-5.000": 40, "5.001-10.000": 50, "+ de 10.001": 0,
    },
    "corte_a": 80, "corte_b": 70, "corte_c": 40,
    "bonus_valor": 1.00,
}

# Fallback para leads/empresas que só têm UF (sem região informada diretamente).
# Quando a região vem preenchida diretamente, ela tem prioridade — ver `regiao_de`.
UF_REGIAO = {
    "AC": "Norte", "AP": "Norte", "AM": "Norte", "PA": "Norte", "RO": "Norte", "RR": "Norte", "TO": "Norte",
    "AL": "Nordeste", "BA": "Nordeste", "CE": "Nordeste", "MA": "Nordeste", "PB": "Nordeste",
    "PE": "Nordeste", "PI": "Nordeste", "RN": "Nordeste", "SE": "Nordeste",
    "DF": "Centro-Oeste", "GO": "Centro-Oeste", "MT": "Centro-Oeste", "MS": "Centro-Oeste",
    "ES": "Sudeste", "MG": "Sudeste", "RJ": "Sudeste", "SP": "Sudeste",
    "PR": "Sul", "RS": "Sul", "SC": "Sul",
}

# Faixas de funcionários usadas pelas regras — na Pesquisa de Leads vêm de um
# select fixo; na Company só existe `num_funcionarios` (inteiro), então
# derivamos a faixa equivalente a partir dele.
FAIXA_LIMITES = [
    (50, "1-50"), (200, "51-200"), (500, "201-500"), (1_000, "501-1.000"),
    (5_000, "1.001-5.000"), (10_000, "5.001-10.000"), (None, "+ de 10.001"),
]


def faixa_de_num_funcionarios(num_funcionarios: int | None) -> str | None:
    if num_funcionarios is None:
        return None
    for limite, faixa in FAIXA_LIMITES:
        if limite is None or num_funcionarios <= limite:
            return faixa
    return None


def regiao_de(regiao: str | None, uf: str | None) -> str | None:
    return regiao or (UF_REGIAO.get(uf) if uf else None)


@dataclass
class IcpBreakdownItem:
    criterio: str
    valor: str
    pontos: int


@dataclass
class IcpResult:
    score: int
    fit: str
    breakdown: list[IcpBreakdownItem] = field(default_factory=list)


def calcular_icp(
    *, setor: str | None, regiao: str | None, uf: str | None,
    faixa_funcionarios: str | None, rules: dict,
) -> IcpResult:
    regiao_efetiva = regiao_de(regiao, uf)
    breakdown: list[IcpBreakdownItem] = []

    setor_pts = 0
    if setor:
        setor_pts = rules["setor"].get(setor, rules["setor_fallback"])
        breakdown.append(IcpBreakdownItem("Setor", setor, setor_pts))

    regiao_pts = 0
    if regiao_efetiva:
        regiao_pts = rules["regiao"].get(regiao_efetiva, 0)
        breakdown.append(IcpBreakdownItem("Região", regiao_efetiva, regiao_pts))

    faixa_pts = 0
    if faixa_funcionarios:
        faixa_pts = rules["faixa_funcionarios"].get(faixa_funcionarios, 0)
        breakdown.append(IcpBreakdownItem("Porte", faixa_funcionarios, faixa_pts))

    score = min(100, setor_pts + regiao_pts + faixa_pts)

    if score == 0 and not setor and not regiao_efetiva and not faixa_funcionarios:
        fit = "Não avaliado"
    elif score >= rules["corte_a"]:
        fit = "A"
    elif score >= rules["corte_b"]:
        fit = "B"
    elif score >= rules["corte_c"]:
        fit = "C"
    else:
        fit = "Sem Perfil"

    return IcpResult(score=score, fit=fit, breakdown=breakdown)
