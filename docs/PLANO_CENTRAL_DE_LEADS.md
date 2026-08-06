# Plano — Central de Leads

Status: **implementado** (backend + frontend, vertical slice completa — ver §8). Protótipo
funcional original em [`docs/prototypes/central_leads_prototype.html`](prototypes/central_leads_prototype.html).

## 0. Decisões travadas

1. **MQL e SQL são sempre transições manuais** — nunca automáticas, mesmo quando o Lead
   Score cruza o corte. A IA pode sugerir ("este lead parece MQL"), mas quem confirma é o
   usuário. `novo→qualificando`, `promovido→novo`, `enrollment→cadência` e `deal criado→
   convertido` continuam automáticos (são fatos do sistema, não julgamento de vendas).
2. **Pesquisa de Leads continua separada** — não funde com a Central de Leads. Pesquisa de
   Leads é pré-CRM (perfil de empresa, sem contato feito); Central de Leads começa depois da
   promoção, quando existe uma `Company`. A ponte entre as duas é só o já existente
   `promoted_company_id`.
3. **Central de Leads mostra todos os estágios, inclusive "Convertido em negócio"** — dá
   noção de taxa de conversão do funil num só lugar. Convertidos ficam fora das contagens de
   "ativos"/"parados" no stat-strip, e um filtro permite escondê-los depois de N dias (não
   somem automaticamente — quem quiser auditar o funil completo consegue).

## 1. Modelo de dados

Tudo aditivo — nenhum campo/enum existente muda de sentido.

### `Company` (`app/models/company.py`)
```python
class FunilEstagio(str, enum.Enum):
    NOVO = "novo"
    QUALIFICANDO = "qualificando"
    CADENCIA = "cadencia"
    MQL = "mql"
    SQL = "sql"
    CONVERTIDO = "convertido"

funil_estagio: Mapped[str | None] = mapped_column(String(20), index=True)
funil_estagio_atualizado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
```
- `None` para empresas que já existiam antes da feature ou que nunca passaram pelo funil de
  leads (import direto, cliente cadastrado manualmente) — a Central de Leads simplesmente não
  lista essas linhas. Não migra dado retroativo por inferência; se quiser, é uma ação manual
  em lote, separada.
- `funil_estagio_atualizado_em` alimenta o cálculo de "parado há X dias" por estágio (distinto
  de `ultima_interacao`, que é sobre contato feito).

Mesmo padrão de coluna computada que `Deal.ultima_interacao` ([`app/models/deal.py:48`](../app/models/deal.py)):
```python
Company.ultima_interacao = column_property(
    select(func.coalesce(func.max(TimelineEvent.created_at), Company.created_at))
    .where(TimelineEvent.company_id == Company.id)
    .correlate_except(TimelineEvent)
    .scalar_subquery()
)
```

### Migração Alembic
Uma revisão nova (`alembic/versions/`), seguindo o padrão de
`fb11856ce211_add_inteligencia_comercial.py`: `ALTER TABLE companies ADD COLUMN
funil_estagio VARCHAR(20), ADD COLUMN funil_estagio_atualizado_em TIMESTAMPTZ`, com índice em
`funil_estagio`. Sem backfill — coluna nasce `NULL` para tudo que já existe.

## 2. Lead Score — extensão de `icp_scoring.py`

Hoje `app/services/icp_scoring.py` calcula só o Fit ICP (perfil da empresa). Proposta: um
segundo módulo `app/services/engagement_scoring.py` com a mesma forma (`dataclass` +
`calcular_engajamento(...)`), que soma pontos por evento de `TimelineEvent` recente e por
progresso em `SequenceEnrollment`, com decaimento por semana sem interação. `Lead Score =
0.6 * score_icp + 0.4 * score_engajamento`, pesos vindos de `IcpScoringRules` estendido
(mesmo objeto de config por tenant que já existe, só com um bloco `engajamento` novo) —
reaproveita o drawer "Critérios de pontuação" já existente na Pesquisa de Leads
([`PesquisaLeadsPage.jsx:951`](../frontend/src/pages/PesquisaLeadsPage.jsx)) em vez de criar
uma tela de configuração paralela.

Pontos de partida sugeridos (ajustáveis pelo admin, como o ICP já é):

| Evento | Pontos |
|---|---|
| E-mail aberto | 8 |
| E-mail respondido | 20 |
| Ligação atendida | 18 |
| Reunião realizada | 30 |
| Visita ao site (rastreio) | 6 |
| Etapa de cadência concluída | 5 |
| Decaimento | −10 por semana sem interação |

## 3. Regras de transição de estágio

| De → Para | Gatilho | Automático? |
|---|---|---|
| `(nenhum)` → `novo` | `LeadProspectService.promote()` grava `funil_estagio='novo'` | Sim |
| `novo` → `qualificando` | Primeira interação registrada na timeline (ligação/e-mail/reunião/nota) | Sim, com toggle por tenant pra desligar se incomodar |
| `*` → `cadencia` | `SequenceEnrollment` criado para a `Company` | Sim |
| `cadencia` → `qualificando` | Enrollment pausado/encerrado sem novo enrollment ativo | Sim |
| `*` → `mql` | Usuário confirma no drawer (dropdown de estágio ou arrastar no kanban) | **Manual sempre** |
| `mql` → `sql` | Usuário confirma | **Manual sempre** |
| `sql` → `convertido` | `Deal` criado com `company_id` desta empresa | Sim (mesmo padrão de `promoted_company_id`) |

Toda transição automática é revertível manualmente (o usuário pode arrastar o card de volta),
e toda mudança de estágio grava um `TimelineEvent` tipo `pipeline` — mesmo padrão já usado
pelas etapas de negócio — pra manter o histórico auditável e alimentar o "Convertido há N dias"
do stat-strip.

## 4. Backend — endpoints

Reaproveita `CompanyRepository`/`CompanyService` (não cria um novo domínio):

- `GET /empresas?funil_estagio=mql&somente_no_funil=true&lead_score_min=70&em_cadencia=true`
  — extensão de filtros do endpoint de Empresas já existente ([`app/api/v1/companies.py`](../app/api/v1),
  `CompanyService.list`), somando `lead_score` e `funil_estagio` ao `CompanyIcpRead` que já
  devolve o ICP hoje.
- `PATCH /empresas/{id}/funil-estagio` — troca manual de estágio (drag no kanban / dropdown no
  drawer), mesmo formato de `CompanyStatusUpdate` que já existe para `status`.
- `GET /empresas/central-leads/resumo` — os agregados do stat-strip (contagem por estágio,
  score médio, parados), pra não recalcular tudo no frontend com a lista completa quando o
  volume crescer.

Nenhuma rota nova de Pesquisa de Leads ou Sequências — Central de Leads só lê o que essas
áreas já produzem (enrollment, timeline, ICP).

## 5. Frontend

- Novo item de menu "Central de Leads" em [`AppShell.jsx`](../frontend/src/layouts/AppShell.jsx),
  grupo "Inteligência Comercial", entre Pesquisa de Leads e Empresas.
- `CentralLeadsPage.jsx` novo, reaproveitando padrões já existentes: kanban com
  drag-and-drop (mesma mecânica visual do board de Negócios), stat-strip e status-pill (mesmo
  CSS de `dataTable.css`/`PesquisaLeadsPage.css`), drawer de detalhe (mesmo `scrim`/`drawer` de
  sempre). Pouco CSS novo — é composição.
- Card de lead no board: empresa, `score-badge` (cor por faixa, como o `fit-badge` do ICP),
  última interação relativa, próxima ação (task aberta mais próxima ou `proxima_acao_sugerida`
  da IA, com selo "sugestão da IA"), selo de cadência ativa (🔁 nome + etapa X/Y), responsável.
- Drawer de detalhe: seletor de estágio (só aqui a transição manual acontece), breakdown do
  score (barra ICP + barra Engajamento), bloco de cadência se houver, próxima ação editável,
  timeline recente, botão "Converter em negócio" quando `sql` (abre o mesmo modal/form de
  criação de negócio já usado em Negócios, pré-preenchido com a empresa).

## 6. Fora de escopo desta primeira fase

- Não altera `CompanyStatus` (lead/qualificado/cliente/perdido/inativo) nem nada que dependa
  dele hoje (Dashboard, relatórios, Pipeline).
- Não migra dado histórico — empresas antigas simplesmente não aparecem na Central de Leads
  até ganharem um `funil_estagio` (via nova promoção, ou ação manual futura de backfill).
- Não mexe em Pesquisa de Leads nem em Sequências — só lê o que elas já gravam.
- Regra de decaimento de engajamento pode rodar como job periódico (Celery, já há
  `app/workers/tasks.py`) recalculando o score, ou como cálculo on-the-fly na consulta — decidir
  na implementação, conforme volume esperado de empresas no funil.

## 7. Sequenciamento sugerido

1. Migração (`funil_estagio`, `funil_estagio_atualizado_em`, `ultima_interacao` computada).
2. `engagement_scoring.py` + extensão de `IcpScoringRules` + endpoint de filtros em Empresas.
3. `PATCH /empresas/{id}/funil-estagio` + gatilhos automáticos (promoção, enrollment, deal).
4. Frontend: `CentralLeadsPage.jsx` (kanban primeiro, lista depois) + item de menu.
5. QA: conferir que nada em Empresas/Negócios/Dashboard mudou de comportamento (mudança é só
   aditiva).

## 8. Implementação — o que foi entregue

Backend: migração [`c1a2b4d6e8f0`](../alembic/versions/c1a2b4d6e8f0_add_funil_estagio_to_companies.py);
`FunilEstagio` + `Company.ultima_interacao` em [`app/models/company.py`](../app/models/company.py);
[`app/services/engagement_scoring.py`](../app/services/engagement_scoring.py) novo; schemas e métodos de
Central de Leads em `app/schemas/company.py` / `app/services/company.py` (`list_central_leads`,
`resumo_central_leads`, `set_funil_estagio`, `get/update_lead_score_rules`); gatilhos automáticos em
`LeadProspectService.promote` (→ novo), `TimelineService.registrar` (→ qualificando),
`SequenceService.enroll` (→ cadência) e `DealService.create` (→ convertido); endpoints
`GET/PATCH /companies/central-leads*` e `GET/PUT /tenant/lead-score-rules`.

Frontend: [`CentralLeadsPage.jsx`](../frontend/src/pages/CentralLeadsPage.jsx) (kanban + lista, drawer de
detalhe, gate de confirmação manual pra MQL/SQL) + item de menu "Central de Leads" + rota
`/central-leads`; pequena extensão aditiva em `NegociosPage.jsx` pra abrir "Novo negócio" pré-preenchido
quando vem do botão "Converter em negócio" do drawer.

Verificado: `pytest` (6 passed), `vite build` (bundle ok), `alembic heads` (head único, cadeia linear),
import completo do FastAPI app + geração do schema OpenAPI confirmando todas as rotas novas registradas
sem conflito.

Não incluído nesta entrega (ver §6, ainda fora de escopo): job periódico de decaimento do score
(calculado on-the-fly na consulta, não persistido), edição inline de "próxima ação" no drawer, e
backfill de `funil_estagio` para empresas antigas.
