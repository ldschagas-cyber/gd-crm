"""Enriquecimento de Pesquisa de Leads via IA (Anthropic + web search).

Nunca escreve no banco: só monta a sugestão. A gravação de fato acontece
via `LeadProspectService.update()` normal, quando o usuário revisa e aceita
as sugestões no frontend — o enriquecimento é só uma fonte de preenchimento
mais rápida do formulário, não um passo automático."""
from app.core.config import settings
from app.core.exceptions import ConflictError
from app.models.lead_prospect import FAIXAS_FATURAMENTO, LeadProspect, SegmentoLead
from app.schemas.lead_prospect import LeadEnrichmentSuggestion
from app.services._ai_json import extract_json

SETORES_CONHECIDOS = [
    "Farma", "Alimentos", "Autopeças", "Etiquetas", "Plástico", "Máquinas e Equipamentos",
    "Química", "Cosmético", "Serviços", "Tecnologia", "Varejo",
]
SEGMENTOS_CONHECIDOS = [s.value for s in SegmentoLead]
FAIXAS_CONHECIDAS = ["1-50", "51-200", "201-500", "501-1.000", "1.001-5.000", "5.001-10.000", "+ de 10.001"]

SYSTEM_PROMPT = f"""Você ajuda um vendedor de uma empresa de governança e cotação de frete rodoviário (GD Conecta) a
pesquisar empresas-alvo (potenciais clientes que despacham/recebem carga rodoviária no Brasil).

Pesquise a empresa informada usando busca na web (site oficial, LinkedIn, notícias, dados públicos de mercado) e
responda SOMENTE com um objeto JSON (sem texto antes ou depois, sem markdown), com exatamente estas chaves:

{{
  "setor": string ou null — escolha um destes se possível: {SETORES_CONHECIDOS}, senão descreva livremente ou use null,
  "segmento": string ou null — classifique o papel da empresa na cadeia logística, escolhendo exatamente uma destas
    opções: {SEGMENTOS_CONHECIDOS},
  "uf": string ou null — sigla de 2 letras do estado brasileiro da sede/planta principal,
  "faixa_funcionarios": string ou null — escolha exatamente uma destas faixas: {FAIXAS_CONHECIDAS},
  "faixa_faturamento": string ou null — estime o faturamento anual e escolha exatamente uma destas faixas:
    {FAIXAS_FATURAMENTO},
  "site": string ou null,
  "telefone": string ou null,
  "linkedin": string ou null — URL do LinkedIn da empresa,
  "contato_sugerido": string ou null — nome e cargo de um decisor plausível (compras/logística/operações) SOMENTE
    se encontrar essa informação publicamente; nunca invente um nome,
  "dor_sugerida": string ou null — 1-2 frases de hipótese sobre uma possível dor logística/de frete desta empresa,
    baseada no setor/porte/operação encontrados (isso é uma hipótese de vendas, pode ser especulativo),
  "observacoes": string ou null — notas curtas sobre confiança dos dados, o que não foi encontrado, ou ambiguidades
}}

Se não encontrar informação confiável para um campo, use null nele — não invente dados, especialmente contato_sugerido."""


class LeadEnrichmentService:
    def enrich(self, lead: LeadProspect) -> LeadEnrichmentSuggestion:
        if not settings.ANTHROPIC_API_KEY:
            raise ConflictError(
                "Enriquecimento por IA ainda não está configurado — falta a ANTHROPIC_API_KEY do servidor."
            )
        import anthropic  # import local: evita custo de import quando a chave não está configurada

        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        conhecido = {
            "setor": lead.setor, "segmento": lead.segmento, "uf": lead.uf,
            "faixa_funcionarios": lead.faixa_funcionarios, "site": lead.site,
        }
        conhecido = {k: v for k, v in conhecido.items() if v}
        contexto = f" Dados já conhecidos (não repita pesquisa nesses, apenas confirme ou complemente o resto): {conhecido}." if conhecido else ""

        response = client.messages.create(
            model=settings.ANTHROPIC_MODEL,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=[{"type": "web_search_20250305", "name": "web_search"}],
            messages=[{
                "role": "user",
                "content": f"Pesquise a empresa: {lead.empresa}.{contexto}",
            }],
        )

        text_blocks = [block.text for block in response.content if getattr(block, "type", None) == "text"]
        if not text_blocks:
            raise ConflictError("A IA não retornou uma resposta de texto. Tente novamente.")

        data = extract_json(text_blocks[-1])
        return LeadEnrichmentSuggestion(**{k: v for k, v in data.items() if k in LeadEnrichmentSuggestion.model_fields})
