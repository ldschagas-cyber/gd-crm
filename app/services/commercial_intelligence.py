"""Inteligência Comercial da Pesquisa de Leads: cruza o perfil da empresa
pesquisado na web com o Benchmark Logístico do GD Diagnóstico para montar um
argumento comercial.

Por que o Diagnóstico entra aqui: o Benchmark Logístico é o próprio produto
que a GD Conecta vende — é o dado proprietário (baseado nos clientes reais)
que nenhum CRM genérico teria. Não é uma feature de benchmark do CRM; o
número é emprestado do Diagnóstico como munição de venda.

Contrato importante: a IA nunca afirma um custo/kg medido para o prospect —
só a média do segmento. Ele não é cliente, não tem CT-e no Diagnóstico; a
comparação real só existe depois da adesão. O número do benchmark é
resolvido de forma determinística em Python (via `BenchmarkClient`) e só
então injetado no prompt como fato já conhecido — a IA nunca calcula esse
valor, só o cita (mesmo princípio de `assistente_tools.py` no Diagnóstico:
"a IA nunca calcula, o backend executa a consulta real").

Nunca escreve no banco — mesmo contrato do LeadEnrichmentService.
"""
from app.core.config import settings
from app.core.exceptions import ConflictError
from app.models.lead_prospect import LeadProspect
from app.schemas.lead_prospect import (
    CommercialIntelligenceBenchmark, CommercialIntelligencePerfil, CommercialIntelligenceResponse,
)
from app.services._ai_json import extract_json
from app.services.benchmark_client import BenchmarkClient

# Setor (taxonomia da Pesquisa de Leads, no CRM) → Segmento (taxonomia do
# Benchmark Setorial, no Diagnóstico). As duas telas usam vocabulários
# diferentes hoje — não é um match automático. Setores sem entrada aqui (ou
# com valor None) simplesmente não têm benchmark disponível; a lista deve
# crescer conforme mais setores forem usados na Pesquisa de Leads.
SETOR_PARA_SEGMENTO: dict[str, str] = {
    "Farma": "DISTRIBUIDOR",
    "Alimentos": "DISTRIBUIDOR",
    "Autopeças": "DISTRIBUIDOR",
    "Química": "DISTRIBUIDOR",
    "Etiquetas": "INDUSTRIA",
    "Plástico": "INDUSTRIA",
    "Máquinas e Equipamentos": "INDUSTRIA",
    "Cosmético": "INDUSTRIA",
    "Varejo": "VAREJO",
}

SYSTEM_PROMPT = """Você ajuda um vendedor de uma empresa de governança e cotação de frete rodoviário (GD Conecta) a
montar um argumento comercial para abordar uma empresa-alvo (potencial cliente que despacha/recebe carga rodoviária
no Brasil).

Pesquise a empresa informada usando busca na web (site oficial, LinkedIn, notícias, dados públicos de mercado) e
responda SOMENTE com um objeto JSON (sem texto antes ou depois, sem markdown), com exatamente estas chaves:

{
  "erp": string ou null — sistema de gestão (ERP) usado pela empresa, se identificável publicamente,
  "porte_estimado": string ou null — 1 frase curta sobre o porte (ex.: "~180 funcionários"),
  "atuacao": string ou null — 1 frase curta sobre onde a empresa opera (estados/regiões),
  "operacao_transporte": string ou null — 1 frase curta sobre indícios de frota própria vs. transportadoras
    terceirizadas, baseada no que encontrar publicamente,
  "argumento": string — 2-4 frases juntando o perfil pesquisado acima com a referência de benchmark informada
    no contexto (quando houver). Nunca afirme um custo/kg medido desta empresa — só cite a média do segmento
    como referência de mercado para abrir a conversa. Se não houver referência de benchmark disponível no
    contexto, monte o argumento a partir do perfil pesquisado por outro ângulo.
}

Se não encontrar informação confiável para um campo do perfil, use null nele — não invente dados."""


class CommercialIntelligenceService:
    def gerar(self, lead: LeadProspect) -> CommercialIntelligenceResponse:
        if not lead.setor:
            raise ConflictError(
                "Defina o setor desta pesquisa antes de gerar a inteligência comercial — "
                "é isso que permite cruzar com o Benchmark Logístico."
            )
        if not settings.ANTHROPIC_API_KEY:
            raise ConflictError(
                "Inteligência Comercial ainda não está configurada — falta a ANTHROPIC_API_KEY do servidor."
            )

        benchmark = self._resolver_benchmark(lead.setor)
        contexto_benchmark = (
            f" Referência de mercado (Benchmark Logístico do Diagnóstico) para o segmento "
            f"{benchmark.segmento_diagnostico}: custo médio de R$ {benchmark.frete_kg_medio:.2f}/kg — "
            f"isso é a média do segmento, NÃO uma medição desta empresa específica."
            if benchmark.disponivel else
            f" Não há referência de Benchmark Logístico disponível para o setor {lead.setor} agora "
            f"({benchmark.motivo_indisponivel}) — monte o argumento sem citar um custo/kg de referência."
        )

        import anthropic  # import local: evita custo de import quando a chave não está configurada

        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        response = client.messages.create(
            model=settings.ANTHROPIC_MODEL,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=[{"type": "web_search_20250305", "name": "web_search"}],
            messages=[{
                "role": "user",
                "content": f"Pesquise a empresa: {lead.empresa}.{contexto_benchmark}",
            }],
        )

        text_blocks = [block.text for block in response.content if getattr(block, "type", None) == "text"]
        if not text_blocks:
            raise ConflictError("A IA não retornou uma resposta de texto. Tente novamente.")

        data = extract_json(text_blocks[-1])
        perfil = CommercialIntelligencePerfil(
            **{k: v for k, v in data.items() if k in CommercialIntelligencePerfil.model_fields}
        )
        argumento = (data.get("argumento") or "").strip()
        if not argumento:
            raise ConflictError("A IA não retornou um argumento comercial. Tente novamente.")

        return CommercialIntelligenceResponse(perfil=perfil, benchmark=benchmark, argumento=argumento)

    def _resolver_benchmark(self, setor: str) -> CommercialIntelligenceBenchmark:
        segmento = SETOR_PARA_SEGMENTO.get(setor)
        if not segmento:
            return CommercialIntelligenceBenchmark(
                disponivel=False, segmento_pesquisado=setor,
                motivo_indisponivel="setor sem segmento de benchmark mapeado",
            )
        try:
            segmentos = BenchmarkClient().listar_segmentos()
        except ConflictError as e:
            return CommercialIntelligenceBenchmark(
                disponivel=False, segmento_pesquisado=setor, segmento_diagnostico=segmento,
                motivo_indisponivel=str(e),
            )
        linha = next((s for s in segmentos if s.get("segmento") == segmento), None)
        if linha is None:
            return CommercialIntelligenceBenchmark(
                disponivel=False, segmento_pesquisado=setor, segmento_diagnostico=segmento,
                motivo_indisponivel="segmento não encontrado no Benchmark Setorial do Diagnóstico",
            )
        return CommercialIntelligenceBenchmark(
            disponivel=True, segmento_pesquisado=setor,
            segmento_diagnostico=linha.get("segmento_rotulo", segmento),
            frete_kg_medio=linha.get("frete_kg_medio"),
        )
