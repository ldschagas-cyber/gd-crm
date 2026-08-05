"""IA do Dossiê Comercial: resumo executivo + próxima ação sugerida (geradas em
background a cada evento relevante da timeline) e resposta a perguntas livres
sobre a empresa. Mesma conta/chave Anthropic já usada em `lead_enrichment.py`.
"""
import json
import re
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import event
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.context import get_current_tenant
from app.core.exceptions import ConflictError, NotFoundError
from app.models.deal import Deal
from app.models.timeline import TimelineEvent
from app.repositories.company import CompanyRepository
from app.repositories.deal import DealRepository
from app.repositories.timeline import TimelineRepository
from app.schemas.company import CompanyAskResponse
from app.services.icp_scoring import DEFAULT_ICP_RULES, calcular_icp, faixa_de_num_funcionarios
from app.services.tenant import TenantService

# Só regenera o resumo pra eventos que carregam informação nova sobre a conta —
# tarefa concluída ou edição de cadastro não mudam o que um vendedor precisa saber.
TIPOS_RELEVANTES = {"ligacao", "email", "reuniao", "nota", "pipeline"}

RESUMO_SYSTEM_PROMPT = """Você é o copiloto de vendas do Argos, o CRM da GD Conecta (governança e cotação de frete
rodoviário para embarcadores industriais no Brasil). Com os dados abaixo sobre uma conta, escreva um resumo
executivo curto pra um vendedor que vai ligar ou se reunir com essa empresa agora e precisa saber tudo em
poucos segundos.

Responda SOMENTE com um objeto JSON (sem texto antes ou depois, sem markdown), com exatamente estas chaves:
{
  "resumo": string — 3 a 5 frases, direto ao ponto: quem é a empresa, o fit ICP, a dor identificada (se
    houver), o estágio da relação e o que falta pra avançar. Nunca invente fatos que não estão nos dados.
  "proxima_acao": string — 1 frase, a ação mais concreta e imediata que o vendedor deveria tomar a seguir,
    baseada no que está pendente nos dados (ex.: um compromisso do contato que ainda não foi cumprido, uma
    etapa do negócio parada, uma informação que falta pra avançar). Se não houver nada pendente óbvio, sugira
    o próximo passo natural do estágio atual.
}"""

ASK_SYSTEM_PROMPT = """Você é o copiloto de vendas do Argos, o CRM da GD Conecta. Responda a pergunta do vendedor
SOMENTE com base nos dados da empresa fornecidos abaixo — nunca invente informação que não está neles. Se os
dados não permitirem responder, diga isso explicitamente.

Responda SOMENTE com um objeto JSON (sem texto antes ou depois, sem markdown), com exatamente estas chaves:
{
  "resposta": string — 1 a 3 frases, direta.
  "fontes": array de strings — quais seções dos dados fornecidos você usou (ex.: ["Timeline", "Negócios"]).
}"""


def _extract_json(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ConflictError("A IA não retornou uma resposta em formato válido. Tente novamente.")
    return json.loads(match.group(0))


class CompanyAiService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = CompanyRepository(db)

    def _get_company(self, company_id: UUID):
        company = self.repo.get(company_id)
        if company is None or company.deleted_at is not None:
            raise NotFoundError("Empresa não encontrada")
        return company

    def _contexto(self, company) -> str:
        tenant = TenantService(self.db).get_current()
        stored = (tenant.config or {}).get("icp_scoring_rules") if tenant.config else None
        rules = {**DEFAULT_ICP_RULES, **(stored or {})}
        faixa = company.porte if company.porte in rules["faixa_funcionarios"] else (
            faixa_de_num_funcionarios(company.num_funcionarios)
        )
        icp = calcular_icp(setor=company.setor, regiao=None, uf=company.uf, faixa_funcionarios=faixa, rules=rules)

        eventos, _ = TimelineRepository(self.db).list_by_company(company.id, offset=0, limit=8)
        deals, _ = DealRepository(self.db).list(Deal.company_id == company.id, offset=0, limit=10,
                                                 order_by=Deal.created_at.desc())

        linhas = [
            f"Empresa: {company.razao_social}",
            f"Segmento: {company.segmento or '—'} | Setor: {company.setor or '—'} | Porte: {company.porte or '—'} "
            f"| Funcionários: {company.num_funcionarios or '—'} | Faturamento estimado: "
            f"{company.faturamento_estimado or '—'}",
            f"Localização: {company.cidade or '—'}/{company.uf or '—'}",
            f"Status no CRM: {company.status}",
            f"Fit ICP: {icp.fit} (score {icp.score}/100)",
            f"Transportadoras usadas: {company.transportadoras or 'não informado'}",
            f"ERP: {company.erp or 'não informado'}",
            f"TMS: {company.tms or 'não informado'}",
            f"Problemas encontrados: {company.problemas_encontrados or 'não informado'}",
            f"Hipóteses: {company.hipoteses or 'não informado'}",
        ]

        if deals:
            linhas.append("Negócios:")
            for d in deals:
                linhas.append(f"  - {d.nome} — status {d.status}, valor previsto {d.valor_previsto or '—'}")
        else:
            linhas.append("Negócios: nenhum registrado")

        if eventos:
            linhas.append("Timeline recente (mais novo primeiro):")
            for e in eventos:
                quando = e.created_at.strftime("%d/%m/%Y")
                linhas.append(f"  - [{e.tipo}] {quando} — {e.titulo}" + (f": {e.descricao}" if e.descricao else ""))
        else:
            linhas.append("Timeline recente: nenhum evento registrado")

        return "\n".join(linhas)

    def _client(self):
        if not settings.ANTHROPIC_API_KEY:
            raise ConflictError("IA do Dossiê Comercial ainda não está configurada — falta a ANTHROPIC_API_KEY do servidor.")
        import anthropic
        return anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    def regenerate_resumo(self, company_id: UUID) -> None:
        """Gera resumo + próxima ação e grava direto no registro (usado pela task
        automática e pelo botão manual 'Atualizar agora')."""
        company = self._get_company(company_id)
        client = self._client()
        response = client.messages.create(
            model=settings.ANTHROPIC_MODEL,
            max_tokens=768,
            system=RESUMO_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": f"Dados da conta:\n\n{self._contexto(company)}"}],
        )
        text_blocks = [b.text for b in response.content if getattr(b, "type", None) == "text"]
        if not text_blocks:
            raise ConflictError("A IA não retornou uma resposta de texto. Tente novamente.")
        data = _extract_json(text_blocks[-1])

        company.resumo_executivo = (data.get("resumo") or "").strip()
        company.proxima_acao_sugerida = (data.get("proxima_acao") or "").strip()
        company.resumo_executivo_atualizado_em = datetime.now(timezone.utc)
        self.repo.save(company)

    def perguntar(self, company_id: UUID, pergunta: str) -> CompanyAskResponse:
        company = self._get_company(company_id)
        client = self._client()
        response = client.messages.create(
            model=settings.ANTHROPIC_MODEL,
            max_tokens=512,
            system=ASK_SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": f"Dados da conta:\n\n{self._contexto(company)}\n\nPergunta do vendedor: {pergunta}",
            }],
        )
        text_blocks = [b.text for b in response.content if getattr(b, "type", None) == "text"]
        if not text_blocks:
            raise ConflictError("A IA não retornou uma resposta de texto. Tente novamente.")
        data = _extract_json(text_blocks[-1])
        return CompanyAskResponse(resposta=data.get("resposta", "").strip(), fontes=data.get("fontes") or [])


def schedule_resumo_regeneration(db: Session, company_id: UUID) -> None:
    """Agenda a regeneração do resumo pra depois que a transação atual commitar —
    mesmo raciocínio de `workflow_events.publish_event`: o worker roda numa conexão
    separada e não pode ler um registro que, do ponto de vista dele, ainda não existe."""
    tenant_id = get_current_tenant()
    if tenant_id is None:
        return

    def _fire(_session):
        from app.workers.tasks import regenerate_company_summary
        regenerate_company_summary.delay(str(tenant_id), str(company_id))

    event.listen(db, "after_commit", _fire, once=True)


def schedule_if_relevant(db: Session, evento: TimelineEvent) -> None:
    if evento.tipo in TIPOS_RELEVANTES:
        schedule_resumo_regeneration(db, evento.company_id)
