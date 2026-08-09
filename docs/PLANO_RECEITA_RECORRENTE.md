# Plano — Gestão de Receita Recorrente (MRR/ARR)

Status: **proposta, não implementada**. Protótipo funcional em
[`docs/prototypes/receita_recorrente_prototype.html`](prototypes/receita_recorrente_prototype.html).

## 0. Decisões travadas

1. **É um domínio novo, não uma extensão de Negócios.** Hoje `Deal` (negócio) modela uma
   venda pontual — fecha (`ganho`/`perdido`) e acabou; não existe nada no schema que
   represente "esse cliente paga X por mês, recorrentemente" ([`app/models/deal.py`](../app/models/deal.py),
   [`app/models/company.py`](../app/models/company.py)). Cuidado para não confundir com
   `Tenant.plano` ([`app/models/tenant.py:25`](../app/models/tenant.py)) — esse é o plano de
   assinatura do **próprio Argos** (SaaS), não o plano que a GD Conecta vende para o cliente
   dela. São dois conceitos homônimos e não relacionados.
2. **Assinatura pertence à `Company`, não ao `Deal`.** Um negócio (`Deal`) pode originar uma
   assinatura quando ganho, mas depois de criada a assinatura vive de forma independente —
   ela sobrevive a upsell, troca de plano, renovação, sem precisar de um novo `Deal` a cada
   evento. `Deal.status = ganho` continua sendo só "a venda foi fechada"; "o cliente está
   pagando quanto agora" é um dado novo, versionado no tempo (ver §1).
3. **v1 não tem catálogo formal de planos** (sem tabela `Plano` com preço/features fixos).
   Cada `Assinatura` guarda `nome_plano` como texto livre (ex.: "Governança Premium") e um
   `valor_mensal` próprio — hoje cada contrato é negociado individualmente e um catálogo
   rígido acrescentaria fricção sem necessidade real ainda. Fica registrado como candidato de
   fase 2 se a GD Conecta padronizar preços por plano (ver §6).
4. **Movimentação de MRR é um livro-razão (ledger), não recalculada por diferença.** Cada
   mudança de valor de uma assinatura (nova venda, upgrade, downgrade, cancelamento,
   reativação) grava um evento imutável em `AssinaturaEvento` com o delta de MRR. Os
   indicadores (Novo MRR, Expansão, Contração, Churn, NRR) do mês são somas desse ledger, não
   inferência por comparação de snapshots — é o jeito padrão de fazer waterfall de MRR de
   forma auditável, e evita divergência quando um valor é editado retroativamente.
5. **Uma assinatura ativa por empresa na v1.** Uma `Company` pode ter várias assinaturas ao
   longo do tempo (histórico), mas só uma com `status = ativa` por vez. Multi-produto
   (cliente pagando por dois planos simultâneos) fica fora de escopo — hoje a GD Conecta
   vende plano único por cliente; force um upgrade de valor em vez de uma segunda linha,
   quando isso mudar.

## 1. Modelo de dados

Domínio novo — dois modelos, ambos tenant-scoped, seguindo os mixins já usados em todo o
projeto (`app/models/base.py`).

### `Assinatura` (`app/models/subscription.py`, novo)
```python
class AssinaturaStatus(str, enum.Enum):
    ATIVA = "ativa"
    PAUSADA = "pausada"      # inadimplência/negociação, sem cancelar
    CANCELADA = "cancelada"

class CicloCobranca(str, enum.Enum):
    MENSAL = "mensal"
    ANUAL = "anual"           # valor_mensal já vem normalizado (valor_anual / 12) — ver §2

class Assinatura(Base, TenantMixin, TimestampMixin):
    __tablename__ = "assinaturas"

    id: Mapped[uuid.UUID] = uuid_pk()
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    deal_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("deals.id"))  # rastreabilidade, opcional
    nome_plano: Mapped[str] = mapped_column(String(120), nullable=False)       # texto livre, ex. "Governança Premium"
    valor_mensal: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)  # MRR desta assinatura, já normalizado
    ciclo_cobranca: Mapped[str] = mapped_column(String(10), nullable=False, default=CicloCobranca.MENSAL.value)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=AssinaturaStatus.ATIVA.value, index=True)
    data_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    data_cancelamento: Mapped[date | None] = mapped_column(Date)
    motivo_cancelamento: Mapped[str | None] = mapped_column(String(255))
    responsavel_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))  # CS owner da conta
```
- Mesmo padrão de coluna computada já usado em `Deal.ultima_interacao`
  ([`app/models/deal.py:48`](../app/models/deal.py)) dá `Assinatura.idade_meses` se for útil
  pra LTV realizado, mas isso é detalhe de implementação, não trava o modelo.
- Índice em `(company_id, status)` — toda tela lê "a assinatura ativa desta empresa" o tempo
  todo (drawer de empresa, cálculo de MRR).

### `AssinaturaEvento` (mesmo arquivo)
```python
class TipoEventoAssinatura(str, enum.Enum):
    NOVA = "nova"
    EXPANSAO = "expansao"       # upgrade de valor
    CONTRACAO = "contracao"     # downgrade de valor, sem cancelar
    CANCELAMENTO = "cancelamento"
    REATIVACAO = "reativacao"   # cliente que cancelou e voltou

class AssinaturaEvento(Base, TenantMixin, TimestampMixin):
    __tablename__ = "assinatura_eventos"

    id: Mapped[uuid.UUID] = uuid_pk()
    assinatura_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("assinaturas.id"), nullable=False, index=True)
    tipo: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    valor_anterior: Mapped[float | None] = mapped_column(Numeric(15, 2))
    valor_novo: Mapped[float | None] = mapped_column(Numeric(15, 2))
    delta_mrr: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)  # valor_novo - valor_anterior (negativo em contração/cancelamento)
    data_evento: Mapped[date] = mapped_column(Date, nullable=False, index=True)  # data de competência, não created_at
    observacao: Mapped[str | None] = mapped_column(Text)
    criado_por: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
```
- `data_evento` é a data de competência (quando o reajuste vale), separada de `created_at`
  (quando alguém registrou no sistema) — pode haver lançamento retroativo, e os indicadores
  mensais agrupam por `data_evento`.
- Toda mudança de `Assinatura.valor_mensal` ou `status` passa **obrigatoriamente** por um
  `AssinaturaEvento` — não existe caminho de código que altera valor/status sem gravar o
  evento correspondente (garantido no `SubscriptionService`, não no banco).

### Migração Alembic
Revisão nova em `alembic/versions/`, seguindo o padrão de
`fb11856ce211_add_inteligencia_comercial.py`: cria `assinaturas` e `assinatura_eventos`,
com FKs para `companies`, `deals` (nullable), `users`, e índices em
`assinaturas(company_id, status)` e `assinatura_eventos(assinatura_id, data_evento)`. Tabelas
novas — sem backfill, sem tocar em `companies`/`deals` existentes.

## 2. Cálculo dos indicadores

Serviço novo `app/services/revenue.py` (`RevenueService`), mesmo formato de
`DashboardService` ([`app/services/dashboard.py`](../app/services/dashboard.py)): recebe
`db: Session`, resolve `tenant_id` via `get_current_tenant()`, expõe um método por indicador
mais um `resumo(periodo)` agregador.

| Indicador | Fórmula | Fonte |
|---|---|---|
| **MRR atual** | `Σ valor_mensal` de `Assinatura` com `status=ativa` | `Assinatura` |
| **ARR** | `MRR atual × 12` | derivado |
| **Novo MRR (mês)** | `Σ delta_mrr` de eventos `tipo=nova` no mês | `AssinaturaEvento` |
| **Expansão MRR (mês)** | `Σ delta_mrr` de eventos `tipo=expansao` no mês | `AssinaturaEvento` |
| **Contração MRR (mês)** | `Σ delta_mrr` de eventos `tipo=contracao` no mês (negativo) | `AssinaturaEvento` |
| **Churn MRR (mês)** | `Σ delta_mrr` de eventos `tipo=cancelamento` no mês (negativo) | `AssinaturaEvento` |
| **MRR líquido novo (mês)** | `Novo + Expansão + Contração + Churn` (contração/churn já negativos) | derivado |
| **Churn de receita (%)** | `\|Churn MRR\| / MRR no início do mês` | derivado |
| **Churn de clientes (%)** (logo churn) | `nº cancelamentos no mês / nº assinaturas ativas no início do mês` | `Assinatura` + eventos |
| **NRR — Net Revenue Retention** | `(MRR início + Expansão + Contração + Churn) / MRR início`, considerando só a base de clientes que já existia no início do período (exclui Novo MRR) | derivado |
| **Ticket médio (ARPA)** | `MRR atual / nº assinaturas ativas` | `Assinatura` |
| **LTV médio** | `ARPA / churn de receita mensal` (LTV = valor esperado ao longo da vida do cliente, no padrão SaaS); exibir também "meses médios de vida" = `1 / churn mensal` como leitura auxiliar | derivado |

Todos os indicadores mensais recebem um `periodo` (mês/ano) igual ao padrão `Periodo` do
dashboard existente ([`app/schemas/dashboard.py`](../app/schemas/dashboard.py)), e o
`resumo()` devolve também a série dos últimos 12 meses para o gráfico de waterfall (§5).

**Por que ledger em vez de comparar snapshots mês a mês:** se recalculássemos Novo/Expansão/
Churn comparando o MRR de um mês com o anterior, uma correção de valor feita hoje mudaria
retroativamente o histórico de meses fechados. Com o ledger, cada evento é datado e imutável
(correção vira um evento novo, não uma edição), então o waterfall de qualquer mês passado
nunca muda depois de fechado — mesma lógica de um livro contábil.

## 3. Regras de escrita — toda mudança gera evento

| Ação do usuário | Efeito em `Assinatura` | Evento gravado |
|---|---|---|
| Criar assinatura (empresa vira cliente recorrente) | `status=ativa`, `valor_mensal=X` | `nova`, `delta_mrr=+X` |
| Aumentar valor (upsell/reajuste) | `valor_mensal: X→Y` (Y>X) | `expansao`, `delta_mrr=+(Y-X)` |
| Reduzir valor (downgrade) | `valor_mensal: X→Y` (Y<X) | `contracao`, `delta_mrr=-(X-Y)` |
| Cancelar | `status=cancelada`, `data_cancelamento` | `cancelamento`, `delta_mrr=-X` |
| Reativar assinatura cancelada | `status=ativa` (mesma linha, se dentro de uma janela razoável) ou nova `Assinatura` | `reativacao`, `delta_mrr=+X` |

Nenhuma transição é automática a partir de `Deal` na v1 — quando um negócio recorrente é
ganho, o vendedor cria a assinatura manualmente a partir da tela da empresa (mesmo padrão de
"Converter em negócio" que já existe pra Central de Leads), com `deal_id` preenchido pra
rastreabilidade. Automatizar isso (criar assinatura sozinho quando `Deal.status=ganho` e o
negócio for marcado como recorrente) é candidato de fase 2 — depende de decidir como
distinguir negócio recorrente de pontual no pipeline, o que hoje não existe.

## 4. Backend — endpoints

Domínio novo `app/api/v1/subscriptions.py` + `app/services/subscription.py` (CRUD e
transições) e `app/services/revenue.py` (indicadores, só leitura):

- `POST /assinaturas` — cria (`company_id`, `nome_plano`, `valor_mensal`, `ciclo_cobranca`,
  `data_inicio`, `deal_id?`), grava evento `nova`.
- `PATCH /assinaturas/{id}/valor` — altera `valor_mensal`, decide `expansao`/`contracao`
  automaticamente pelo sinal do delta, grava evento.
- `PATCH /assinaturas/{id}/cancelar` — `motivo_cancelamento`, `data_cancelamento`, grava
  evento `cancelamento`.
- `PATCH /assinaturas/{id}/reativar` — grava evento `reativacao`.
- `GET /assinaturas?status=ativa&responsavel_id=&plano=` — lista para a tabela principal.
- `GET /empresas/{id}/assinaturas` — histórico de assinaturas de uma empresa (card no
  detalhe da empresa).
- `GET /receita/resumo?periodo=mes` — `RevenueService.resumo()`: os KPIs do stat-strip +
  série de 12 meses pro waterfall.
- `GET /receita/waterfall?meses=12` — série detalhada (Novo/Expansão/Contração/Churn por mês),
  separado do resumo pra não pesar a chamada principal quando o gráfico não estiver visível.

## 5. Frontend

- Novo item de menu **"Receita"** em [`AppShell.jsx`](../frontend/src/layouts/AppShell.jsx),
  grupo próprio (não é "Inteligência Comercial" nem "CRM" — é uma área de Customer
  Success/Financeiro), com submenu único por ora: "Receita Recorrente".
- `ReceitaRecorrentePage.jsx` novo, reaproveitando padrões existentes (stat-strip, tabela
  `dataTable.css`, drawer) — sem biblioteca de gráficos nova, mesmo approach 100% CSS/SVG já
  usado no projeto (não há `recharts`/`d3`/etc. no [`package.json`](../frontend/package.json)):
  - **Stat-strip**: MRR atual, ARR, Novo MRR (mês), Expansão (mês), Churn % (receita), NRR %,
    LTV médio.
  - **Waterfall de MRR**: barras empilhadas por mês (Novo + Expansão em verde/azul, Contração
    + Churn em vermelho, linha de MRR líquido) — últimos 12 meses.
  - **Tabela de assinaturas ativas**: empresa, plano, MRR, ciclo, início, responsável,
    `status-pill`; clique abre o drawer de detalhe.
  - **Drawer de detalhe**: dados da assinatura, ações (editar valor / cancelar / reativar) e
    timeline de `AssinaturaEvento` (mesmo componente visual `.timeline-mini` do protótipo de
    Central de Leads).
- Integração pontual em [`CompanyDetailPage.jsx`](../frontend/src/pages/CompanyDetailPage.jsx):
  card "Assinatura" mostrando a assinatura ativa (ou botão "Criar assinatura" se a empresa é
  `status=cliente` e não tem nenhuma) — mesmo espírito do card de Dossiê Comercial que já
  existe lá.
- `getRevenueSummary`/`getSubscriptions` novos em `frontend/src/api/`, mesmo padrão de
  `frontend/src/api/dashboards.js`.

## 6. Fora de escopo desta primeira fase

- **Catálogo formal de planos** (tabela `Plano` com preço/features padronizados) — v1 usa
  texto livre por assinatura (§0.3). Migrar pra catálogo depois é aditivo: adicionar
  `plano_id` opcional em `Assinatura` sem quebrar o texto livre existente.
- **Automação Deal→Assinatura** — criação de assinatura a partir de negócio ganho continua
  manual (§3).
- **Cobrança de fato** (emissão de boleto/NF, integração com gateway de pagamento) — este
  plano é só o **registro e a leitura** de receita recorrente pra métricas de gestão, não um
  módulo de faturamento. Se a GD Conecta usa um sistema de cobrança externo (ex. gateway,
  ERP), a integração futura seria: webhook do sistema externo → grava `AssinaturaEvento`,
  mantendo o CRM como fonte de indicadores mas não como emissor de cobrança.
- **Multi-produto por cliente** (duas assinaturas ativas simultâneas) — §0.5.
- **Previsão/forecast de MRR futuro** — os indicadores são todos sobre o passado/presente;
  projeção seria fase 3, depois de ter histórico real suficiente pra validar um modelo.
- **Cohort analysis** (retenção por safra de cliente) — útil, mas é uma segunda tela inteira;
  o ledger de eventos já deixa isso possível de construir depois sem mudar o modelo de dados.

## 7. Sequenciamento sugerido

1. Migração (`assinaturas`, `assinatura_eventos`).
2. `app/services/subscription.py` (CRUD + transições que sempre gravam evento) + endpoints
   `POST/PATCH /assinaturas`.
3. `app/services/revenue.py` (cálculo dos indicadores) + `GET /receita/resumo` e
   `GET /receita/waterfall`.
4. Frontend: `ReceitaRecorrentePage.jsx` (stat-strip + tabela primeiro, waterfall depois) +
   item de menu "Receita".
5. Card de assinatura em `CompanyDetailPage.jsx`.
6. QA: nenhuma tabela/endpoint existente muda de comportamento — mudança é inteiramente
   aditiva, como a Central de Leads.
