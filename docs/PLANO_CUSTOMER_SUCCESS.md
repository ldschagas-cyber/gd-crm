# Plano — Customer Success

Status: **proposta, não implementada**. Protótipo funcional em
[`docs/prototypes/customer_success_prototype.html`](prototypes/customer_success_prototype.html).

## 0. Diagnóstico — por que essa é a maior lacuna

O Argos hoje cobre bem o funil até a venda: Pesquisa de Leads → Central de Leads (proposta) →
Empresas/Negócios → Pipeline ganho. A partir daí, **o rastro para** — `Deal.status = ganho` não
dispara nada, `Company.status` não muda sozinho para `cliente` (conferido em
[`app/services/deal.py:97`](../app/services/deal.py), o `move_stage` só atualiza o próprio negócio) e
não existe hoje nenhum módulo, campo ou endpoint que responda a "esse cliente está bem atendido?",
"o contrato dele renova quando?", "ele está usando o que comprou?". RevOps de verdade fecha o
loop pós-venda de volta para Marketing/Vendas (expansão, referência, churn como sinal). Esse é o
propósito deste plano.

## 1. Decisões travadas

1. **Customer Success não cria uma entidade "Cliente" separada** — reaproveita `Company` com
   `status = cliente`, no mesmo espírito da Central de Leads reaproveitando `Company` com
   `funil_estagio` em vez de duplicar cadastro. Uma empresa é lead, depois cliente; é a mesma
   linha na tabela `companies`, só muda de módulo em que aparece.
2. **A ponte venda → pós-venda é um gatilho automático que hoje não existe e precisa ser criado**:
   quando um `Deal` entra numa etapa `StageType.GANHO`, além de fechar o negócio
   (`deal.py:97-99`), grava `Company.status = cliente` (se ainda não for) e inicia a fase de CS
   (`cs_fase = implantacao`). Isso é aditivo ao `move_stage` existente, não uma reescrita.
3. **Fase de CS (`cs_fase`) é um campo novo, independente de `CompanyStatus`** — mesma lógica do
   `funil_estagio` da Central de Leads: aditivo, não redefine o que `status` já significa hoje em
   Dashboard/Pipeline/Empresas.
4. **Renovação e expansão reaproveitam `Deal`** — uma oportunidade de upsell/expansão é um negócio
   novo (`origem = "expansao"` ou `"renovacao"`, mesmo `company_id`), não uma segunda entidade de
   oportunidade. Isso mantém Dashboard e relatórios de pipeline já existentes enxergando esse
   valor sem trabalho extra.
5. **Uso da plataforma é dado que o Argos não possui de origem** — o Argos é a ferramenta de venda
   da GD Conecta, não o produto que o tenant vende ao cliente final (frete, logística — a julgar
   pelos campos `transportadoras`/`erp`/`tms` já existentes em `Company`). Não dá para fabricar
   "uso" sem uma fonte real. Fase 1 trata isso como **dado manual do CSM** (check-in periódico);
   fica um endpoint de ingestão aberto para quando/se existir integração com o produto do tenant.
6. **Health Score é honesto sobre o que é medido vs. inferido** — como ICP/Engajamento na Central
   de Leads, é um composto com pesos configuráveis, não uma IA opaca. Detalhe na seção 3.

## 2. Modelo de dados

Tudo aditivo — nenhuma coluna/enum existente muda de sentido.

### `Company` (`app/models/company.py`) — novas colunas

```python
class CsFase(str, enum.Enum):
    IMPLANTACAO = "implantacao"
    ATIVO = "ativo"
    EM_RISCO = "em_risco"
    EM_EXPANSAO = "em_expansao"
    CHURN = "churn"

cs_fase: Mapped[str | None] = mapped_column(String(20), index=True)
cs_fase_atualizada_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
cs_responsavel_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
mrr: Mapped[float | None] = mapped_column(Numeric(12, 2))
data_inicio_contrato: Mapped[date | None] = mapped_column(Date)
data_renovacao: Mapped[date | None] = mapped_column(Date, index=True)
health_score: Mapped[int | None] = mapped_column(Integer)
health_score_atualizado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
esta_inadimplente: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
```

- `cs_responsavel_id` é **separado** de `responsavel_id` (o vendedor que fechou pode não ser quem
  acompanha o pós-venda) — mesmo padrão de dois papéis já visto em `Task.responsavel_id` vs.
  `Deal.responsavel_id`.
- `None` em `cs_fase` para toda empresa que nunca passou por um negócio ganho (igual à decisão do
  `funil_estagio` na Central de Leads: sem backfill retroativo por inferência).

### `OnboardingChecklistItem` (novo, `app/models/onboarding.py`)

```python
class OnboardingChecklistItem(Base, TenantMixin, TimestampMixin):
    __tablename__ = "onboarding_checklist_items"

    id: Mapped[uuid.UUID] = uuid_pk()
    company_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True)
    titulo: Mapped[str] = mapped_column(String(255), nullable=False)
    ordem: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pendente")  # pendente | concluido
    prazo: Mapped[date | None] = mapped_column(Date)
    concluido_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    responsavel_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
```

Itens são criados a partir de um **template por tenant** (lista fixa configurável, análoga aos
critérios de ICP) no momento em que `cs_fase` vira `implantacao`. Não reaproveita `Task` porque
onboarding precisa de uma lista fixa e reordenável por padrão de produto, o que `Task` (criada
solta, uma a uma) não modela bem.

### Registro de check-in de saúde (reaproveita `TimelineEvent`, não cria tabela nova)

Novo valor em `TimelineType`: `CS_CHECKIN = "cs_checkin"`. Um check-in do CSM grava um
`TimelineEvent` com `evento_meta = {uso_percebido, nps, satisfacao, notas}` — mesmo padrão de
`metadata` JSONB já usado por outros tipos de evento. O `health_score` da `Company` é recalculado
a partir do check-in mais recente + sinais já existentes na timeline, sem precisar de uma tabela
dedicada.

### Migração Alembic

Uma revisão nova, seguindo `fb11856ce211_add_inteligencia_comercial.py` como referência: `ALTER
TABLE companies ADD COLUMN cs_fase ..., ADD COLUMN mrr ...` etc., mais `CREATE TABLE
onboarding_checklist_items`. Sem backfill.

## 3. Health Score — `app/services/health_scoring.py`

Mesmo formato de `icp_scoring.py`/`engagement_scoring.py` (dataclass + função pura +
`IcpScoringRules`-like config por tenant, reaproveitando o mesmo mecanismo de "pesos
configuráveis pelo admin" já existente).

| Pilar | Peso | Fonte | Observação |
|---|---|---|---|
| Engajamento | 30% | `TimelineEvent` da empresa (contatos do CSM), decaimento por semana sem interação | Mesma fórmula proposta para o Engajamento da Central de Leads — reuso direto |
| Adoção/Uso | 25% | Campo `uso_percebido` do check-in mais recente | Manual na fase 1 (decisão 5); endpoint `POST /empresas/{id}/uso-eventos` fica aberto para ingestão automática futura |
| Satisfação | 20% | `nps`/`satisfacao` do check-in mais recente | Registro simples, não pesquisa automatizada (fora de escopo, §5) |
| Financeiro | 25% | `esta_inadimplente` + proximidade de `data_renovacao` sem interação recente | Sinal duro: inadimplência ou renovação próxima sem contato derruba o score mesmo com os outros pilares bem |

Corte sugerido (ajustável): **Saudável ≥ 70**, **Atenção 40–69**, **Em risco < 40** — mesma
linguagem visual de "quente/morno/frio" já usada no `score-badge` da Central de Leads.

## 4. Regras de transição de `cs_fase`

| De → Para | Gatilho | Automático? |
|---|---|---|
| `(nenhum)` → `implantacao` | `Deal` entra em etapa `StageType.GANHO` → grava `Company.status = cliente` (se ainda não) + cria itens do checklist a partir do template do tenant | Sim (gatilho novo — fecha o gap descrito em §0) |
| `implantacao` → `ativo` | Todos os itens do checklist concluídos | Sim, com botão manual "Concluir implantação" para o CSM assumir o controle antes disso |
| `ativo` → `em_risco` | `health_score` cruza abaixo do corte, ou `data_renovacao` a menos de 30 dias sem interação nos últimos 14 dias | Sim — é um alerta, não um avanço de funil comercial; reversível a qualquer momento |
| `em_risco` → `ativo` | `health_score` volta a cruzar o corte | Sim |
| `ativo`/`em_risco` → `em_expansao` | Usuário abre um `Deal` com `origem = "expansao"` para essa empresa | Sim |
| `em_expansao` → `ativo` | O negócio de expansão fecha (ganho ou perdido) | Sim |
| `*` → `churn` | Usuário confirma cancelamento no drawer | **Manual sempre** — mesmo princípio de MQL/SQL na Central de Leads: julgamento de negócio não é automático |

Toda transição grava `TimelineEvent` tipo `pipeline` (mesmo padrão já usado por Negócios e pela
Central de Leads), mantendo histórico auditável.

## 5. Backend — endpoints

Reaproveita `CompanyRepository`/`CompanyService`, mais um serviço novo `OnboardingService`:

- `GET /clientes?cs_fase=em_risco&health_score_max=40&renovacao_ate=2026-10-01` — extensão de
  filtros do endpoint de Empresas já existente, mesmo padrão da Central de Leads.
- `PATCH /empresas/{id}/cs` — edita `cs_responsavel_id`, `mrr`, datas de contrato, fase manual
  (troca de fase pelo dropdown/kanban).
- `GET /empresas/{id}/implantacao` / `PATCH /empresas/{id}/implantacao/{item_id}` — checklist de
  onboarding.
- `POST /empresas/{id}/checkins` — registra check-in (uso percebido, NPS, satisfação, notas) como
  `TimelineEvent` e dispara recálculo do `health_score`.
- `GET /clientes/resumo` — agregados do stat-strip (MRR total, ARR, health médio, renovações em
  30/60/90 dias, quantidade em risco), mesmo racional do `/empresas/central-leads/resumo`
  proposto na Central de Leads.
- Negócios de expansão/renovação usam o endpoint de Negócios já existente — só filtram por
  `origem`.

## 6. Frontend

- Novo grupo de menu **"Customer Success"** em
  [`AppShell.jsx`](../frontend/src/layouts/AppShell.jsx), logo após "CRM", com item "Clientes".
- `ClientesPage.jsx`: kanban por `cs_fase` (Implantação → Ativo → Em risco → Em expansão →
  Encerrado) + visão em lista, reaproveitando a mesma mecânica de drag-and-drop, stat-strip e
  status-pill já usados/propostos na Central de Leads — pouco CSS novo.
- Card do cliente no board: empresa, `health-badge` (mesma lógica visual do `score-badge`), MRR,
  dias até renovação, CSM responsável, selo "sem check-in há N dias" quando aplicável.
- Detalhe do cliente: um drawer mais largo com abas internas —
  **Visão Geral** (dados, CSM, MRR, próxima ação) · **Implantação** (checklist com progresso) ·
  **Saúde** (breakdown do score por pilar) · **Uso da Plataforma** (métricas do check-in mais
  recente, com aviso de que é dado manual até existir integração) · **Resultados** (KPIs
  combinados com o cliente) · **Renovação & Expansão** (datas de contrato, MRR/ARR, negócios de
  expansão vinculados, botão "Abrir negócio de expansão" que pré-preenche o mesmo formulário já
  usado em Negócios).

## 7. Fora de escopo desta primeira fase

- Não cria portal do cliente (self-service) nem pesquisa de NPS automatizada por e-mail — check-in
  é preenchido pelo CSM; automação de envio fica para fase 2, podendo reaproveitar Workflows.
- Não integra com o produto real do tenant para captar uso automaticamente — decisão 5. O endpoint
  de ingestão fica pronto, mas vazio, até existir uma fonte real.
- Não cria motor de billing/faturamento — `mrr` é informativo para o cálculo de MRR/ARR do CS, não
  substitui um sistema financeiro.
- Não altera `CompanyStatus` além de automatizar a transição para `cliente` já prevista
  implicitamente pelo enum existente (não cria um novo valor de status).

## 8. Sequenciamento sugerido

1. Migração (`cs_fase`, `cs_responsavel_id`, `mrr`, datas de contrato, `health_score`,
   `onboarding_checklist_items`) + gatilho `Deal` ganho → `Company.status = cliente` /
   `cs_fase = implantacao` (fecha o gap descrito em §0).
2. `OnboardingService` (checklist + template por tenant) + endpoints.
3. `health_scoring.py` + endpoint de check-in + recálculo.
4. Regras de transição automática de fase (§4) como parte do `CompanyService`.
5. Frontend: `ClientesPage.jsx` (lista primeiro, kanban depois) + drawer com abas + item de menu.
6. QA: conferir que nada em Empresas/Negócios/Dashboard mudou de comportamento para quem não usa
   CS (mudança é só aditiva) — mesmo checklist de QA da Central de Leads.

## 9. Como isso conversa com a Central de Leads

Os dois planos compartilham o mesmo modelo mental: `Company` ganha um "estágio de módulo"
(`funil_estagio` / `cs_fase`) sem mexer no `status` legado, transições automáticas são só fatos do
sistema, e julgamento de negócio (MQL/SQL/Churn) é sempre manual. Implementados juntos, o fluxo
completo fica: **Pesquisa de Leads → Central de Leads → Negócio ganho → Customer Success**, com
`Deal` sendo o único ponto de conversão em ambas as pontas (criação de negócio fecha a Central de
Leads; negócio ganho abre o Customer Success).
