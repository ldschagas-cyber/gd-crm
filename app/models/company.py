"""Company — empresas (leads e clientes) do tenant."""
import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func, select
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, column_property, mapped_column

from app.models.base import Base, SoftDeleteMixin, TenantMixin, TimestampMixin, uuid_pk
from app.models.timeline import TimelineEvent


# Origem do cadastro — lista fixa pra dar filtro/relatório limpo (mesmo espírito de
# ORIGENS_LEAD em lead_prospect.py). O Negócio herda esse valor da empresa na criação
# (ver DealService.create) em vez de ter origem própria — ver app/services/deal.py.
ORIGENS_EMPRESA = [
    "Indicação", "Prospecção ativa", "Feira", "Campanha", "LinkedIn",
    "Site institucional", "Formulário do site", "Pesquisa de Leads", "Outro",
]


class CompanyStatus(str, enum.Enum):
    LEAD = "lead"
    QUALIFICADO = "qualificado"
    CLIENTE = "cliente"
    PERDIDO = "perdido"
    INATIVO = "inativo"


class FunilEstagio(str, enum.Enum):
    """Estágio no funil da Central de Leads — independente de `CompanyStatus` (que
    continua regendo lead/cliente/perdido). `None` = empresa nunca entrou no funil
    (não aparece na Central de Leads). MQL e SQL são sempre transição manual — nunca
    atingidos automaticamente pelo Lead Score. Ver docs/PLANO_CENTRAL_DE_LEADS.md."""
    NOVO = "novo"
    QUALIFICANDO = "qualificando"
    CADENCIA = "cadencia"
    MQL = "mql"
    SQL = "sql"
    CONVERTIDO = "convertido"


class CsFase(str, enum.Enum):
    """Fase de Customer Success — independente de `CompanyStatus` e de `FunilEstagio`
    (que regem, respectivamente, lead/cliente/perdido e o funil pré-venda). `None` =
    empresa nunca teve um negócio ganho (não aparece no módulo de Clientes). Ver
    docs/PLANO_CUSTOMER_SUCCESS.md §4. `CHURN` só é atingido via cancelamento de
    `Assinatura` (AssinaturaService.cancelar) — nunca por PATCH direto de fase, pra não
    existir uma fase "encerrado" que discorde do estado real de cobrança."""
    IMPLANTACAO = "implantacao"
    ATIVO = "ativo"
    EM_RISCO = "em_risco"
    EM_EXPANSAO = "em_expansao"
    CHURN = "churn"


class Company(Base, TenantMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "companies"
    __table_args__ = (
        UniqueConstraint("tenant_id", "cnpj", name="uq_company_tenant_cnpj"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    razao_social: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    nome_fantasia: Mapped[str | None] = mapped_column(String(255))
    cnpj: Mapped[str | None] = mapped_column(String(14))
    site: Mapped[str | None] = mapped_column(String(255))
    linkedin: Mapped[str | None] = mapped_column(String(255))
    telefone: Mapped[str | None] = mapped_column(String(20))
    email: Mapped[str | None] = mapped_column(String(255))
    endereco: Mapped[str | None] = mapped_column(String(255))
    cidade: Mapped[str | None] = mapped_column(String(120))
    uf: Mapped[str | None] = mapped_column(String(2))
    segmento: Mapped[str | None] = mapped_column(String(120))
    porte: Mapped[str | None] = mapped_column(String(40))
    num_funcionarios: Mapped[int | None] = mapped_column(Integer)
    faturamento_estimado: Mapped[float | None] = mapped_column(Numeric(15, 2))
    # Faixa de faturamento em texto (ex.: "R$ 25–100 milhões") vinda da Pesquisa de Leads —
    # mesmo padrão de `porte`/faixa_funcionarios: não dá pra converter faixa em número exato
    # sem inventar dado, então fica como tag na ficha até alguém preencher
    # faturamento_estimado com o valor exato (se/quando descobrir).
    faixa_faturamento: Mapped[str | None] = mapped_column(String(60))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=CompanyStatus.LEAD.value, index=True)
    # Desde quando `status` está no valor atual — gravado em CompanyService.set_status().
    # Alimenta o SLA Comercial por status (ver docs/PLANO_SLA_COMERCIAL.md e
    # app/services/activity_sla.py); distinto de `funil_estagio_atualizado_em` abaixo, que é
    # sobre o estágio da Central de Leads, não sobre `status`. NULL pra empresas que já
    # existiam antes desta coluna — SLA por status simplesmente não se aplica a elas até a
    # próxima mudança de status (sem backfill por inferência).
    status_atualizado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    origem: Mapped[str | None] = mapped_column(String(80))
    responsavel_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    created_by: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))

    # Central de Leads — funil pós-promoção (ver FunilEstagio acima). NULL = fora do funil.
    funil_estagio: Mapped[str | None] = mapped_column(String(20), index=True)
    funil_estagio_atualizado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Customer Success — fase pós-venda (ver CsFase acima). NULL = empresa nunca teve um
    # negócio ganho; passa a ser preenchida automaticamente por DealService quando um
    # negócio entra em etapa GANHO (ver CompanyService.advance_cs_on_deal_ganho).
    cs_fase: Mapped[str | None] = mapped_column(String(20), index=True)
    cs_fase_atualizada_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # CSM responsável pelo pós-venda — separado de `responsavel_id` (o vendedor que fechou
    # pode não ser quem acompanha o cliente depois). Default automático: quem fechou o
    # negócio; reatribuível livremente depois.
    cs_responsavel_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    # Health Score (0-100) — composto de engajamento/uso/satisfação/financeiro, recalculado
    # a cada check-in ou evento relevante (ver app/services/health_scoring.py). NULL até o
    # primeiro cálculo (empresa acabou de virar cliente, ainda sem nenhum sinal).
    health_score: Mapped[int | None] = mapped_column(Integer)
    health_score_atualizado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Nota curta de personalização, usada em {{contexto_rapido}} nos e-mails automáticos
    # (ver app/services/sequence_dispatch.py:render_template) — equivalente, em nível de
    # empresa, ao contexto_pessoal do Contato.
    contexto_rapido: Mapped[str | None] = mapped_column(Text)

    # Setor — taxonomia do motor de Score ICP (app/services/icp_scoring.py), distinta
    # de `segmento` (texto livre). Preenchida na promoção de um LeadProspect ou
    # manualmente, pra empresa poder ter score/fit calculado no Dossiê Comercial.
    setor: Mapped[str | None] = mapped_column(String(80))

    # Dossiê Comercial — resumo executivo gerado por IA, regenerado automaticamente
    # a cada evento relevante na timeline (ver app/services/company_ai.py).
    resumo_executivo: Mapped[str | None] = mapped_column(Text)
    proxima_acao_sugerida: Mapped[str | None] = mapped_column(Text)
    resumo_executivo_atualizado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Dossiê Comercial — stack operacional, preenchimento manual do vendedor na descoberta.
    transportadoras: Mapped[str | None] = mapped_column(Text)
    erp: Mapped[str | None] = mapped_column(String(120))
    tms: Mapped[str | None] = mapped_column(String(120))

    # Dossiê Comercial — descoberta, texto livre.
    problemas_encontrados: Mapped[str | None] = mapped_column(Text)
    hipoteses: Mapped[str | None] = mapped_column(Text)

    # Contato indicado na Pesquisa de Leads (nome/cargo em texto livre, ex.: "Ana Paula —
    # Gerente de Compras") — não é um Contato de verdade (sem e-mail/telefone estruturado),
    # só um ponto de partida pro vendedor até cadastrar o contato real. Só chega aqui por
    # cópia automática em LeadProspectService.promote(); também editável na empresa.
    contato_sugerido: Mapped[str | None] = mapped_column(String(255))

    # SDR Argos — dossiê comercial do prospector, gerado direto na empresa (JSON de
    # CommercialIntelligenceRecord: perfil + benchmark + argumento + gravado_em). Roda
    # automaticamente no handoff da promoção (LeadProspectService.promote) e sob demanda
    # via botão "SDR Argos" (SdrArgosService) — ver docs/PLANO_SDR_AUTONOMO.md §0.5.
    # Não é mais copiado de LeadProspect.inteligencia_comercial (decisão travada nº 3: a
    # Inteligência Comercial passou a ser estritamente pós-promoção).
    inteligencia_comercial: Mapped[str | None] = mapped_column(Text)
    # Cadência sugerida pelo SDR Argos — JSON com sequence_id/sequence_nome/contato/passos.
    # É SUGESTÃO, nunca inscrição automática (decisão travada nº 6): a inscrição de verdade
    # continua sendo um SequenceEnrollment criado deliberadamente pelo vendedor, com esta
    # sugestão pré-preenchida no formulário.
    cadencia_sugerida: Mapped[str | None] = mapped_column(Text)
    # Roteiro de ligação gerado pelo SDR Argos a partir do dossiê — só texto de apoio para o
    # vendedor humano ligar; o agente nunca fala com o prospect (decisão travada nº 8).
    roteiro_ligacao: Mapped[str | None] = mapped_column(Text)
    # Quando o SDR Argos rodou pela última vez nesta empresa (auto na promoção, ou manual).
    sdr_argos_atualizado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


# Data/hora da última interação registrada na timeline desta empresa — mesmo padrão de
# Deal.ultima_interacao (app/models/deal.py), usado pela Central de Leads pra "última
# interação" e pra marcar lead parado. Cai pro created_at da própria empresa sem eventos.
Company.ultima_interacao = column_property(
    select(func.coalesce(func.max(TimelineEvent.created_at), Company.created_at))
    .where(TimelineEvent.company_id == Company.id)
    .correlate_except(TimelineEvent)
    .scalar_subquery()
)
