"""SDR Argos — o prospector (nível 2 do agente comercial em dois níveis, ver
docs/PLANO_SDR_AUTONOMO.md). Roda estritamente pós-promoção, sobre uma `Company`:
monta o dossiê comercial (perfil + Benchmark Logístico + argumento), sugere a
cadência de contato e o roteiro de ligação, e grava tudo direto na empresa —
mesmo padrão do resumo executivo em `company_ai.py`, do qual este serviço é uma
expansão (decisão travada nº 5).

Nível 1 (o aprendiz, dados básicos + Fit ICP) continua em `lead_enrichment.py`,
na Pesquisa de Leads — nunca gera argumento nem cadência.

Contrato: a IA nunca afirma um custo/kg medido para o prospect, só a média do
segmento (o Benchmark Logístico é resolvido de forma determinística em Python
e injetado no prompt como fato já conhecido). Nunca inventa contato — nome/
e-mail sem fonte confiável ficam como
já estavam no dossiê (ver LeadEnrichmentService), este serviço não lida com
descoberta de contato (ver PLANO_SDR_AUTONOMO.md §6 — provedor de dados B2B,
ainda não implementado).

Nunca dispara contato externo: a cadência é sempre SUGESTÃO (decisão travada
nº 6) — a inscrição de verdade é um SequenceEnrollment criado deliberadamente
pelo vendedor, via SequenceService.enroll, fora deste serviço."""
import json
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import event, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import ConflictError, NotFoundError
from app.models.company import Company
from app.models.sequence import Sequence
from app.repositories.company import CompanyRepository
from app.schemas.lead_prospect import (
    CommercialIntelligenceBenchmark, CommercialIntelligencePerfil, CommercialIntelligenceRecord,
)
from app.services._ai_json import extract_json
from app.services.benchmark_client import BenchmarkClient
from app.services.timeline import TimelineService

# Setor (taxonomia da Pesquisa de Leads, no CRM) → Segmento (taxonomia do Benchmark
# Setorial, no Diagnóstico). As duas telas usam vocabulários diferentes hoje — não é um
# match automático. Setores sem entrada aqui (ou com valor None) simplesmente não têm
# benchmark disponível; a lista deve crescer conforme mais setores forem usados.
# Movido de app/services/commercial_intelligence.py (removido — ver decisão travada nº 3).
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

SYSTEM_PROMPT = """Você é o SDR Argos, o prospector de uma empresa de governança e cotação de frete rodoviário
(GD Conecta). A empresa informada já foi qualificada e promovida a cliente-alvo — seu trabalho é montar o dossiê
que um vendedor humano vai usar para abordá-la, e SUGERIR (nunca decidir sozinho) como prosseguir.

Pesquise a empresa usando busca na web (site oficial, LinkedIn, notícias, dados públicos de mercado) e responda
SOMENTE com um objeto JSON (sem texto antes ou depois, sem markdown), com exatamente estas chaves:

{
  "erp": string ou null — sistema de gestão (ERP) usado, se identificável publicamente,
  "porte_estimado": string ou null — 1 frase curta sobre o porte (ex.: "~180 funcionários"),
  "atuacao": string ou null — 1 frase curta sobre onde a empresa opera (estados/regiões),
  "operacao_transporte": string ou null — 1 frase curta sobre indícios de frota própria vs. transportadoras
    terceirizadas, baseada no que encontrar publicamente,
  "argumento": string — 2-4 frases juntando o perfil pesquisado com a referência de benchmark informada no
    contexto (quando houver). Nunca afirme um custo/kg medido desta empresa — só cite a média do segmento como
    referência de mercado para abrir a conversa. Se não houver referência de benchmark, monte o argumento a
    partir do perfil pesquisado por outro ângulo,
  "roteiro_ligacao": string — um roteiro curto (abertura, dor a confirmar, ponte para o benchmark, fechamento),
    em 4-6 linhas, para o VENDEDOR HUMANO usar numa ligação — você nunca liga, só prepara quem liga
}

Se não encontrar informação confiável para um campo, use null nele — não invente dados."""


class SdrArgosService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = CompanyRepository(db)
        self.timeline = TimelineService(db)

    def _get_company(self, company_id: UUID) -> Company:
        company = self.repo.get(company_id)
        if company is None or company.deleted_at is not None:
            raise NotFoundError("Empresa não encontrada")
        return company

    def _resolver_benchmark(self, setor: str | None) -> CommercialIntelligenceBenchmark:
        # Resolução determinística — só varia de commercial_intelligence.py (removido) por
        # aceitar `setor` direto (Company já tem a coluna) em vez de um LeadProspect inteiro.
        if not setor:
            return CommercialIntelligenceBenchmark(
                disponivel=False, segmento_pesquisado=setor,
                motivo_indisponivel="empresa sem setor definido",
            )
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

    def _sugerir_cadencia(self, company: Company) -> dict | None:
        """Sugestão heurística de qual sequência ativa usar — primeira sequência ativa do
        tenant. É um ponto de partida deliberadamente simples: a régua de "melhor sequência
        para este perfil" ainda não existe (ver PLANO_SDR_AUTONOMO.md, fora de escopo desta
        fatia); o vendedor sempre pode trocar no formulário de inscrição. NUNCA inscreve —
        só monta o preview que o botão "Inscrever na cadência" usa para pré-preencher."""
        sequence = self.db.execute(
            select(Sequence).where(Sequence.tenant_id == company.tenant_id, Sequence.ativo.is_(True))
            .order_by(Sequence.created_at)
        ).scalars().first()
        if sequence is None:
            return None
        return {
            "sequence_id": str(sequence.id),
            "sequence_nome": sequence.nome,
            "contato_sugerido": company.contato_sugerido,
        }

    def _client(self):
        if not settings.ANTHROPIC_API_KEY:
            raise ConflictError("SDR Argos ainda não está configurado — falta a ANTHROPIC_API_KEY do servidor.")
        import anthropic  # import local: evita custo de import quando a chave não está configurada
        return anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    def gerar(self, company_id: UUID) -> Company:
        """Gera o dossiê + argumento + roteiro e sugere a cadência, gravando tudo direto na
        empresa. Chamado automaticamente no handoff da promoção (ver `schedule_sdr_argos`
        abaixo) e sob demanda pelo botão "SDR Argos". Não dispara nenhum contato externo."""
        company = self._get_company(company_id)
        client = self._client()
        benchmark = self._resolver_benchmark(company.setor)
        contexto_benchmark = (
            f" Referência de mercado (Benchmark Logístico do Diagnóstico) para o segmento "
            f"{benchmark.segmento_diagnostico}: custo médio de R$ {benchmark.frete_kg_medio:.2f}/kg — "
            f"isso é a média do segmento, NÃO uma medição desta empresa específica."
            if benchmark.disponivel else
            f" Não há referência de Benchmark Logístico disponível agora "
            f"({benchmark.motivo_indisponivel}) — monte o argumento sem citar um custo/kg de referência."
        )

        response = client.messages.create(
            model=settings.ANTHROPIC_MODEL,
            max_tokens=1280,
            system=SYSTEM_PROMPT,
            # Mesma variante com dynamic filtering usada em lead_enrichment/commercial_intelligence
            # (suportada pelo Sonnet 5) — max_uses=2: o benchmark já vem resolvido no contexto, a
            # pesquisa aqui é sobre ERP/porte/atuação/operação/roteiro, não sobre achar a empresa.
            tools=[{"type": "web_search_20260209", "name": "web_search", "max_uses": 2}],
            messages=[{
                "role": "user",
                "content": f"Empresa: {company.razao_social}.{contexto_benchmark}",
            }],
        )

        text_blocks = [b.text for b in response.content if getattr(b, "type", None) == "text"]
        if not text_blocks:
            raise ConflictError("O SDR Argos não retornou uma resposta de texto. Tente novamente.")
        data = extract_json(text_blocks[-1])

        perfil = CommercialIntelligencePerfil(
            **{k: v for k, v in data.items() if k in CommercialIntelligencePerfil.model_fields}
        )
        argumento = (data.get("argumento") or "").strip()
        if not argumento:
            raise ConflictError("O SDR Argos não retornou um argumento comercial. Tente novamente.")
        roteiro = (data.get("roteiro_ligacao") or "").strip() or None

        record = CommercialIntelligenceRecord(
            perfil=perfil, benchmark=benchmark, argumento=argumento,
            gravado_em=datetime.now(timezone.utc),
        )
        company.inteligencia_comercial = record.model_dump_json()
        company.roteiro_ligacao = roteiro
        cadencia = self._sugerir_cadencia(company)
        company.cadencia_sugerida = json.dumps(cadencia) if cadencia else None
        company.sdr_argos_atualizado_em = datetime.now(timezone.utc)
        company = self.repo.save(company)

        self.timeline.registrar(
            company_id=company.id, tipo="sdr", titulo="SDR Argos gerou o dossiê comercial",
            descricao="Argumento cruzado com o Benchmark Logístico"
            + (f" · sugeriu \"{cadencia['sequence_nome']}\"" if cadencia else "") + ".",
        )
        return company


def schedule_sdr_argos(db: Session, company_id: UUID) -> None:
    """Agenda o SDR Argos para depois que a transação atual commitar — mesmo raciocínio de
    `company_ai.schedule_resumo_regeneration`: o worker roda numa conexão separada e não
    pode ler uma empresa que, do ponto de vista dele, ainda não existe. Chamado no handoff
    da promoção (LeadProspectService.promote, só quando cria empresa nova — reaproveitar
    uma empresa existente não deve reprocessar o dossiê dela).

    Captura `tenant_id` do contexto AGORA (enquanto a request/serviço que chamou ainda está
    autenticado) — não dá pra deduzir depois, dentro da task: ver o comentário em
    `run_sdr_argos_task` sobre por que ela também não lê o tenant da própria Company."""
    from app.core.context import get_current_tenant

    tenant_id = get_current_tenant()
    if tenant_id is None:
        return

    def _fire(_session):
        from app.workers.tasks import run_sdr_argos_task
        run_sdr_argos_task.delay(str(tenant_id), str(company_id))

    event.listen(db, "after_commit", _fire, once=True)
