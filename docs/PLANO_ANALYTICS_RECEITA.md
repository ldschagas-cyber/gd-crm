# Plano — Analytics de Receita (Revenue Analytics)

Status: **proposta, não implementada**. Protótipo funcional em
[`docs/prototypes/analytics_receita_prototype.html`](prototypes/analytics_receita_prototype.html).

## 0. Diagnóstico do estado atual

O [`DashboardPage.jsx`](../frontend/src/pages/DashboardPage.jsx) +
[`DashboardService`](../app/services/dashboard.py) de hoje respondem "como está a operação
agora": negócios abertos por etapa, SLA estourado, execução de sequências, tarefas do vendedor.
Tudo é **estoque no instante presente** (`Deal.status == 'aberto'`) ou **contagem simples do
período** (`negocios_criados`, `receita_ganha`).

O que falta — e é isso que RevOps pede — é **fluxo ao longo do tempo desde antes do CRM**: quantas
empresas entraram no topo do funil, quanto sobrou em cada etapa, quanto custou converter, e o
retorno disso. Hoje isso não existe em nenhuma tela:

- Não há uma etapa "empresas pesquisadas" no dashboard — `LeadProspect` (Pesquisa de Leads,
  pré-CRM) nunca aparece nos indicadores.
- Não há contagem de reuniões como etapa de funil — `TimelineEvent.tipo == 'reuniao'` só existe
  na timeline de cada empresa, não agregado.
- Não existe conceito de custo/investimento comercial em lugar nenhum do schema — impossível
  calcular CAC ou ROI hoje.
- `taxa_conversao` no dashboard atual é só "negócios ganhos ÷ negócios fechados no período"
  (conversão dentro do funil de negócio) — não é conversão de topo a base (pesquisa → cliente).

Esta proposta é **aditiva**: uma tela nova, um serviço novo, uma tabela nova. Não altera
`DashboardService`, `CommercialDashboard` nem nada do dashboard operacional existente.

## 1. Decisões travadas

1. **Funil de 5 checkpoints fixos nesta fase**, não um funil livre configurável por tenant (isso
   fica pra fase 2, se aparecer demanda real). Cada checkpoint é definido sobre uma tabela que já
   existe — ver §2. O objetivo é sair rápido com algo correto, não construir um motor de funil
   genérico especulativamente.
2. **Contagem por período de entrada, não estoque atual.** Cada etapa conta quantas
   empresas/negócios **entraram** nela dentro do período selecionado (mês/trimestre/ano/custom) —
   mesmo padrão que `negocios_criados` já usa no dashboard atual. Isso é diferente de cohort
   tracking (acompanhar a mesma leva de 1000 empresas até o fim) — ver nota no §2 e §6.
3. **O rótulo da 4ª etapa é configurável, o dado por trás não.** No exemplo do pedido ela se chama
   "Diagnóstico"; nem toda empresa vai chamar assim (pode ser "Proposta", "Oportunidade"). O dado
   que a alimenta é sempre "negócio (`Deal`) aberto" — é o evento mais próximo que o sistema já
   registra desse momento do processo comercial. O rótulo fica em `Tenant.config` (mesmo campo
   JSONB onde já mora a config de ICP Scoring), não vira uma tabela nova.
4. **Investimento comercial é lançamento manual nesta fase**, não integração com Google/Meta Ads
   nem folha de pagamento. Um valor por mês/categoria, editável por admin/gestor. Automatizar a
   captura fica para quando houver um caso de uso concreto de integração.
5. **Tela nova, endpoint novo, sem tocar no dashboard operacional.** RevOps e o vendedor olham
   coisas diferentes — a proposta não tenta unificar as duas telas.

## 2. Funil — mapeamento de cada etapa

| # | Etapa (rótulo padrão) | Fonte de dado | Regra |
|---|---|---|---|
| 1 | Empresas pesquisadas | `LeadProspect` | `COUNT(*)` onde `created_at` no período |
| 2 | Leads | `Company` | `COUNT(*)` onde `created_at` no período (cobre tanto promovidas da Pesquisa de Leads quanto criadas direto em Empresas — `Company` já é a entidade canônica de "lead" no schema, `CompanyStatus.LEAD` é o default) |
| 3 | Reuniões realizadas | `TimelineEvent` tipo `reuniao` | `COUNT(DISTINCT company_id)` onde `created_at` no período (1ª reunião da empresa nesse período conta uma vez; reuniões extras na mesma empresa não inflam a etapa) |
| 4 | Diagnóstico *(rótulo configurável)* | `Deal` | `COUNT(DISTINCT company_id)` onde `created_at` no período (negócio aberto = melhor proxy hoje pro momento pós-diagnóstico) |
| 5 | Clientes | `Deal` status `ganho` | `COUNT(DISTINCT company_id)` onde `data_fechamento` no período |

Cada etapa é uma query independente e simples (mesmo estilo das queries do `DashboardService`
atual) — nenhuma etapa depende da anterior ter sido "a mesma empresa" (não é cohort). Isso é uma
simplificação deliberada: um funil por período (`% de conversão etapa a etapa neste mês`) em vez
de rastrear a jornada individual de cada empresa. É o suficiente pros indicadores pedidos
(conversão por etapa, CAC, ROI) e é ordens de grandeza mais simples de implementar e de explicar
pro usuário do que cohort tracking. Fase 2, se necessário — ver §6.

### Tempo médio por etapa

Aproximação fase 1, sem cohort exato: idade média da empresa (`created_at` até o evento) no
momento em que cruza cada checkpoint — ex. "tempo médio entre `Company.created_at` e a 1ª
`TimelineEvent` tipo reunião" para a etapa Lead→Reunião, mesmo padrão de cálculo que
`Deal.ultima_interacao` já usa (subquery com `func.min`/`func.max` sobre `TimelineEvent`,
[`app/models/deal.py:48`](../app/models/deal.py)). É uma média por etapa no período, não o tempo
de uma coorte específica atravessando o funil inteiro.

## 3. Modelo de dados novo

### `RevenueInvestment` (`app/models/revenue_investment.py`) — tabela nova

```python
class InvestmentCategory(str, enum.Enum):
    MARKETING = "marketing"
    VENDAS = "vendas"
    FERRAMENTAS = "ferramentas"
    OUTROS = "outros"

class RevenueInvestment(Base, TenantMixin, TimestampMixin):
    __tablename__ = "revenue_investments"

    id: Mapped[uuid.UUID] = uuid_pk()
    competencia: Mapped[date] = mapped_column(Date, nullable=False, index=True)  # dia 1 do mês
    categoria: Mapped[str] = mapped_column(String(20), nullable=False)
    valor: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    observacao: Mapped[str | None] = mapped_column(String(255))
    criado_por: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
```

Um lançamento por mês/categoria (marketing, vendas, ferramentas, outros) — soma vira
"investimento comercial do período" pro cálculo de CAC/ROI. Migração Alembic nova, mesmo padrão
de `fb11856ce211_add_inteligencia_comercial.py`.

### `Tenant.config`

Chave nova `analytics_receita.rotulo_etapa_diagnostico` (default `"Diagnóstico"`) — reaproveita o
JSONB que já existe, sem migração de schema pra isso.

## 4. Backend — endpoints

Serviço novo `app/services/revenue_analytics.py` (`RevenueAnalyticsService`), não mexe em
`DashboardService`:

- `GET /analytics/revenue-funnel?periodo=mes|trimestre|ano|custom&inicio=&fim=` — as 5 etapas,
  conversão etapa-a-etapa, conversão geral (etapa 5 ÷ etapa 1), tempo médio por etapa.
- `GET /analytics/revenue-summary?periodo=...` — CAC (`investimento ÷ clientes novos`), ROI
  (`(receita_ganha − investimento) ÷ investimento`), ticket médio, receita ganha, investimento
  total do período.
- `GET /analytics/revenue-investments?competencia_inicio=&competencia_fim=` — lista lançamentos.
- `POST /analytics/revenue-investments` / `PUT .../{id}` / `DELETE .../{id}` — CRUD do
  investimento, restrito a `admin`/`gestor` (`require_roles`, mesmo guard do
  `/dashboards/commercial` atual).

## 5. Frontend

- Novo item de menu **"Analytics de Receita"** em [`AppShell.jsx`](../frontend/src/layouts/AppShell.jsx),
  grupo próprio "Analytics" (ou dentro de "Inteligência Comercial" — decidir na implementação),
  visível só pra `admin`/`gestor` — mesma régua de acesso do dashboard comercial hoje
  (`GESTAO_PERFIS` em `DashboardPage.jsx`).
- `RevenueAnalyticsPage.jsx` novo:
  - Filtro de período (mês/trimestre/ano/personalizado) — reaproveita o padrão `segmented` já
    usado no Dashboard atual.
  - Funil visual grande (5 barras), contagem + % de conversão da etapa anterior + tempo médio,
    mesmo componente visual do `.funnel` que já existe no dashboard (`PipelineFunnelCard`),
    generalizado pra aceitar rótulo/contagem/conversão arbitrários em vez de etapas de pipeline.
  - KPI row: CAC, ROI, Ticket médio, Receita ganha, Investimento no período, Conversão geral do
    funil.
  - Tabela de lançamentos de investimento (CRUD inline, mês + categoria + valor).
  - Fora do MVP mas fácil de anexar depois: breakdown por origem (`Company.origem`) ou por
    vendedor (`responsavel_id`), reaproveitando o padrão de pivot já usado em
    `_sequence_execution`/`SequenceExecutionCard`.

## 6. Fora de escopo desta primeira fase

- Cohort tracking exato (acompanhar a mesma leva de empresas atravessando as 5 etapas ao longo do
  tempo, com lag real por empresa) — a fase 1 entrega conversão e tempo médio por período, que já
  responde as perguntas do pedido original; cohort é uma evolução natural se o negócio pedir depois.
- Funil configurável por tenant (etapas customizáveis, reordenáveis) — só o rótulo da etapa 4 é
  configurável nesta fase.
- LTV (Lifetime Value) e atribuição multi-canal de marketing.
- Integração automática de investimento (Google Ads, Meta Ads, folha de pagamento) — lançamento é
  manual.
- Não altera `DashboardService`, `CommercialDashboard`, `SellerDashboard` nem nada do dashboard
  operacional hoje.

## 7. Sequenciamento sugerido

1. Migração: tabela `revenue_investments`.
2. `RevenueAnalyticsService` — as 5 queries do funil + agregados de CAC/ROI (reaproveitando o
   estilo de query do `DashboardService` atual).
3. Endpoints (`/analytics/revenue-funnel`, `/analytics/revenue-summary`,
   `/analytics/revenue-investments` CRUD).
4. Frontend: `RevenueAnalyticsPage.jsx` (funil + KPIs primeiro, CRUD de investimento depois) +
   item de menu.
5. QA: conferir que nada em Dashboard/Empresas/Negócios mudou de comportamento (mudança é só
   aditiva) e que o acesso fica restrito a `admin`/`gestor`.
