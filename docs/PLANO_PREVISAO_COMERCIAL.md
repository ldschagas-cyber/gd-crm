# Plano — Previsão Comercial (Forecast/Compromisso) e integração com Metas do Funil

Status: **implementado** (backend + frontend, §1–7 e §8 — ver §7 e §8.8). Protótipo funcional em
[`docs/prototypes/previsao_comercial_prototype.html`](prototypes/previsao_comercial_prototype.html)
(inclui a página Previsão Comercial — com o cartão CAC & ROI do §8 — e a integração visual com
Metas do Funil, navegáveis no mesmo arquivo).

> Este documento absorveu o antigo `PLANO_ANALYTICS_RECEITA.md`. Aquele plano começou propondo
> uma tela nova de "Analytics de Receita"; checando o que já existia, o funil e a receita por
> vendedor já eram cobertos aqui e em `PLANO_METAS_FUNIL.md` — a única parte genuinamente nova
> (CAC/ROI) virou extensão deste documento em vez de um plano/tela à parte (ver §8 e o ponto 6 do
> §3 acima, na versão navegável do protótipo).

## 0. Contexto

Pedido: cobrir o item "Forecast" do quadro de Pipeline Comercial — receita prevista,
probabilidade, data de fechamento, pipeline por vendedor e "compromisso" — e avaliar se esse
processo se encaixa no que já existe em Metas do Funil ([`PLANO_METAS_FUNIL.md`](PLANO_METAS_FUNIL.md)).

## 1. Análise de viabilidade

**Quase tudo já existia.** `Deal` já tinha `valor_previsto`, `probabilidade`,
`data_prev_fechamento` e `responsavel_id` — o cálculo de forecast ponderado
(`valor × probabilidade / 100`) já roda hoje por etapa no Kanban
([`NegociosPage.jsx`](../frontend/src/pages/NegociosPage.jsx), coluna "Valor ponderado" do board).
O único conceito novo é **Compromisso**: um sinalizador manual, por negócio, com que o vendedor
assume "esse fecha esse mês" — distinto da probabilidade ponderada (que é inferida da etapa,
não uma promessa).

**Modelo adotado**: `Deal.commit: bool`, default `False`, editável pelo vendedor no board, na
ficha do negócio e na própria tela de Previsão Comercial. Sem tabela nova.

## 2. Fórmulas

Para um conjunto de negócios abertos com `data_prev_fechamento` dentro do mês selecionado:

- **Pipeline** = Σ `valor_previsto`
- **Forecast** = Σ `valor_previsto × probabilidade / 100` — mesma fórmula já usada no rodapé
  de cada coluna do Kanban, agora agregada por mês/vendedor em vez de por etapa.
- **Compromisso** = Σ `valor_previsto` apenas dos negócios com `commit = true`

Quebra "Pipeline por vendedor": mesmas três somas agrupadas por `responsavel_id`.

Regra de acesso: quem não é `admin`/`gestor` só vê o próprio recorte — o `responsavel_id`
informado na query é ignorado e substituído pelo do usuário autenticado (mesmo padrão de
`GET /dashboards/seller` vs. `GET /dashboards/commercial`).

## 3. Integração com Metas do Funil — decisão

**Não fundir num único número.** As duas telas medem coisas diferentes:

| | Metas do Funil | Previsão Comercial |
|---|---|---|
| Unidade | Contagem (empresas/negócios) | R$ |
| População | As 7 etapas — a maior parte é `LeadProspect`/`Company`, nem toca `Deal` | Só negócios abertos |
| Janela | Coorte ou atividade de período fechado (histórico) | Prospectivo — o que fecha *este mês* |

Empilhar as duas num único número misturaria unidade e janela de tempo. Em vez disso:

1. **Ponto de junção real**: as duas últimas linhas do funil de contagem ("Propostas
   enviadas", "Clientes fechados") já são baseadas em `Deal`, via `PipelineStage.marco_funil`
   (ver [`PLANO_METAS_FUNIL.md` §5](PLANO_METAS_FUNIL.md)). `FunilMetasResumo` ganhou dois
   campos aditivos e opcionais — `propostas_valor_aberto` (soma de `valor_previsto` dos
   negócios abertos na(s) etapa(s) marcada(s) `marco_funil="proposta"`) e
   `fechados_valor_realizado` (soma de `valor_previsto` dos negócios `ganho` no período) —
   calculados reaproveitando a mesma tag, sem inventar um segundo critério de "quais negócios
   contam". `None` quando o tenant não tem etapa marcada (mesmo comportamento de fallback que
   o resto do Anexo 1 já tem pra `marco_funil`).
2. **Menu**: "Previsão Comercial" entra no grupo "Inteligência Comercial", ao lado de "Central
   de Leads" e "Metas do Funil" — não em "CRM" (perto de "Negócios"), que foi minha primeira
   proposta e não seguia o padrão já adotado pelas telas irmãs.
3. Isto é a extensão que o próprio [`PLANO_METAS_FUNIL.md` §9](PLANO_METAS_FUNIL.md) já listava
   como fora de escopo da primeira entrega: "metas por vendedor/pipeline individual". A quebra
   por vendedor do Compromisso/Forecast é essa extensão, chegando pela porta da receita.
4. Front: `FunilMetasPage` mostra os dois valores como um chip discreto sob as linhas
   "Propostas enviadas"/"Clientes fechados" do funil de contagem (só quando não-nulos), com
   link direto para `/previsao-comercial`.

## 4. Backend — o que foi entregue

- Migração `add_commit_to_deals` — `deals.commit boolean not null default false`.
- `Deal.commit` em [`app/models/deal.py`](../app/models/deal.py); exposto em `DealRead` e
  editável via `DealUpdate` (`PUT /deals/{id}` já aceita payload parcial — nenhum endpoint novo
  precisou ser criado pra isso).
- `ForecastService` novo ([`app/services/forecast.py`](../app/services/forecast.py)) —
  `resumo(mes, current_user, pipeline_id=None, responsavel_id=None)`; agregação pura testável
  em `_aggregate` (mesmo espírito de `_montar_resumo` em `FunilMetasService`).
- Endpoint `GET /forecast/resumo?mes=AAAA-MM&pipeline_id=&responsavel_id=` — qualquer usuário
  autenticado pode chamar; o serviço restringe o recorte a `responsavel_id = usuário atual`
  quando o perfil não é `admin`/`gestor`.
- `FunilMetasResumo.propostas_valor_aberto` / `.fechados_valor_realizado` (§3.1), calculados em
  `FunilMetasService.resumo()`.

## 5. Frontend — o que foi entregue

- [`PrevisaoComercialPage.jsx`](../frontend/src/pages/PrevisaoComercialPage.jsx) novo — rota
  `/previsao-comercial`, item de menu "Previsão Comercial" no grupo Inteligência Comercial
  ([`AppShell.jsx`](../frontend/src/layouts/AppShell.jsx)). Seletor de mês, filtro de vendedor
  (só gestor/admin vê o filtro — vendedor já recebe seu próprio recorte da API), 3 KPIs
  (Pipeline/Forecast/Compromisso), tabela por vendedor, lista de negócios do mês com checkbox de
  Compromisso editável ali mesmo.
- Checkbox de Compromisso também no board de Negócios (ícone de estrela no card do Kanban e na
  lista) e na ficha do negócio ([`DealDetailPage.jsx`](../frontend/src/pages/DealDetailPage.jsx))
  — é o vendedor quem marca, nos três lugares onde ele já trabalha, não só na tela nova.
- [`FunilMetasPage.jsx`](../frontend/src/pages/FunilMetasPage.jsx): chip de receita sob as
  linhas "Propostas enviadas"/"Clientes fechados", link "Ver por vendedor →" para
  `/previsao-comercial`.

## 6. Fora de escopo desta entrega

- Meta de receita do mês (o protótipo tem um campo "Meta" editável na cobertura, mas ele é só
  local ao componente — não persiste; persistir precisaria de um campo novo em `tenants.config`,
  fica pra quando isso for pedido de verdade).
- Séries históricas de acurácia (forecast previsto x realizado, mês a mês) — o protótipo simula
  isso pro mês fechado; a API não devolve série, só o mês consultado (mesmo racional do §9 do
  plano de Metas do Funil).
- Forecast por pipeline quando há mais de um pipeline ativo — o filtro `pipeline_id` existe na
  API, mas o front hoje assume o pipeline padrão (mesmo comportamento de `NegociosPage`).

## 7. Verificação

`pytest` (ver `tests/test_forecast.py`), `alembic heads` (head único), `vite build`.

## 8. Extensão — CAC & ROI

Rodando Metas do Funil e Previsão Comercial lado a lado, a única coisa que uma proposta de
"Analytics de Receita" pedia e que não existe em lugar nenhum do schema é **custo/investimento
comercial** — sem isso, CAC e ROI são impossíveis de calcular. É a única peça genuinamente nova;
o resto (funil, receita por vendedor) já é coberto pelas seções 1–7 acima e por
`PLANO_METAS_FUNIL.md`.

### 8.1 Decisões

1. **Não é uma tela nova.** É um cartão adicional na própria `PrevisaoComercialPage.jsx` — ver
   mockup no cartão "CAC & ROI comercial" do protótipo, entre "Cobertura da meta do mês" e
   "Pipeline por vendedor".
2. **Receita e contagem de clientes vêm de dado que já existe** — não recalcula nada:
   - Clientes novos do mês = `FunilMetasResumo` etapa `fechados` (modo atividade).
   - Receita ganha do mês = `FunilMetasResumo.fechados_valor_realizado` (já existe, §3 acima).
   - O único dado que falta é o lado do custo.
3. **Investimento é lançamento manual** — sem integração com Ads/folha de pagamento nesta fase.
4. **CAC e ROI são por mês**, não por vendedor/etapa — custo de aquisição não se fatia por etapa
   do funil, só ponta a ponta; e como não há responsável dono de um lançamento de investimento,
   quebrar por vendedor exigiria inventar um rateio arbitrário.

### 8.2 Modelo de dados novo

Só uma tabela — o resto é leitura do que já existe (8.1.2):

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

Migração Alembic nova, mesmo padrão de `add_commit_to_deals` (aditiva, sem backfill).

### 8.3 Fórmulas

- **Investimento do mês** = Σ `RevenueInvestment.valor` onde `competencia` cai no mês consultado.
- **CAC** = investimento do mês ÷ `FunilMetasResumo` etapa `fechados` (real, modo atividade) do
  mesmo mês.
- **ROI** = (`fechados_valor_realizado` − investimento) ÷ investimento.

### 8.4 Backend — endpoints

Serviço novo `app/services/revenue_investment.py` (`RevenueInvestmentService`) — CRUD simples +
um agregador que chama `FunilMetasService.resumo()` internamente em vez de duplicar suas queries:

- `GET /revenue-investments?competencia_inicio=&competencia_fim=` / `POST` / `PUT .../{id}` /
  `DELETE .../{id}` — CRUD do lançamento, restrito a `admin`/`gestor` (`require_roles`, mesmo
  guard de `/dashboards/commercial`).
- `GET /revenue-investments/cac-roi?mes=AAAA-MM` — devolve `{investimento_total, clientes_novos,
  receita_realizada, cac, roi}`, calculado a partir de `RevenueInvestment` (soma direta) +
  `FunilMetasService.resumo("atividade", mes)` (reaproveitado, não reimplementado).

Nenhuma rota nova de funil/conversão — isso já existe em `/funil-metas/resumo`.

### 8.5 Frontend

- Cartão **"CAC & ROI comercial"** dentro de `PrevisaoComercialPage.jsx`, entre o cartão de
  cobertura de meta (já existe) e a quebra por vendedor (já existe) — mesmo `kpi-mini`/
  `integration-pill` já usados no cartão "Previsão de Receita" de `FunilMetasPage`.
  - Selo `integration-pill` "dado vem de Metas do Funil".
  - Tabela de lançamentos de investimento (mês, categoria, valor) — CRUD inline.
- Nenhuma mudança em `FunilMetasPage.jsx` além de, opcionalmente, um segundo chip "CAC: R$ X"
  ao lado do chip de receita que já existe sob a linha "Clientes fechados".

### 8.6 Fora de escopo

- Qualquer recontagem de funil/etapas/conversão — isso é `PLANO_METAS_FUNIL.md`.
- Qualquer recálculo de receita/pipeline/forecast — isso já é §1–7 deste documento.
- Integração automática de investimento (Google Ads, Meta Ads, folha de pagamento).
- LTV e atribuição multi-canal de marketing.
- CAC/ROI por vendedor ou por origem — extensão natural, não bloqueante, mesmo racional do §9 de
  `PLANO_METAS_FUNIL.md` pra outras quebras por vendedor.

### 8.7 Sequenciamento sugerido

1. Migração: tabela `revenue_investments`.
2. `RevenueInvestmentService` — CRUD + `cac_roi(mes)` chamando `FunilMetasService.resumo()`.
3. Endpoints (`/revenue-investments` CRUD, `/revenue-investments/cac-roi`).
4. Frontend: cartão "CAC & ROI" em `PrevisaoComercialPage.jsx` + painel de lançamentos.
5. QA: conferir que nada em Metas do Funil/Previsão Comercial muda de comportamento (mudança é só
   aditiva — nenhuma query existente é alterada, só reaproveitada).

### 8.8 Implementação — o que foi entregue

Backend: migração [`b6d2a91f4c7e`](../alembic/versions/b6d2a91f4c7e_add_revenue_investments.py)
(`revenue_investments`, aditiva); `RevenueInvestment`/`InvestmentCategory` em
[`app/models/revenue_investment.py`](../app/models/revenue_investment.py);
`RevenueInvestmentRepository` (`app/repositories/revenue_investment.py`, sem query própria — só
`BaseRepository` genérico); `RevenueInvestmentService`
([`app/services/revenue_investment.py`](../app/services/revenue_investment.py)) — CRUD +
`cac_roi(mes)`, que chama `FunilMetasService.resumo("atividade", mes)` pra clientes
fechados/receita realizada e faz só a soma do investimento e a conta de CAC/ROI (`_compute`,
separada em função pura pra ser testável sem banco, mesmo espírito de `ForecastService._aggregate`
e `FunilMetasService._montar_resumo`). Endpoints em
[`app/api/v1/revenue_investments.py`](../app/api/v1/revenue_investments.py) — `GET/POST
/revenue-investments`, `PUT/DELETE /revenue-investments/{id}`, `GET
/revenue-investments/cac-roi?mes=`; todos restritos a `admin`/`gestor`
(`require_roles`, mesmo guard de `/dashboards/commercial`) — vendedor não vê custo.
`CacRoiResumo.cac`/`.roi` são `None` (não `0`) quando o denominador é zero, pra não confundir
"indefinido" com "grátis"/"sem retorno".

Frontend: `CacRoiCard` novo dentro de
[`PrevisaoComercialPage.jsx`](../frontend/src/pages/PrevisaoComercialPage.jsx) — só renderiza pra
`admin`/`gestor` (mesmo `GESTAO_PERFIS` que já filtra o filtro de vendedor nessa tela), entre a
legenda de cobertura e o grid "Pipeline por vendedor". Reaproveita `.stat-strip`/`.stat-tile` (já
usados pelos 3 KPIs Pipeline/Forecast/Compromisso da mesma página) e `table.data`/`.icon-btn`
(dataTable.css) em vez de CSS novo — só o necessário
([`PrevisaoComercialPage.css`](../frontend/src/pages/PrevisaoComercialPage.css) ganhou um bloco
pequeno pro selo de integração, pontinhos de categoria e o formulário inline de lançamento).
Cliente de API em [`frontend/src/api/revenueInvestments.js`](../frontend/src/api/revenueInvestments.js).

Verificado: `pytest` (46 passed, incluindo os 10 testes novos de `_periodo_bounds`/`_compute` em
[`tests/test_revenue_investment.py`](../tests/test_revenue_investment.py)); `alembic heads` (head
único, cadeia linear); import completo do FastAPI app + geração do schema OpenAPI confirmando as
5 rotas novas registradas sem conflito; `vite build` (279 módulos, sem erro). A migração não foi
executada contra um Postgres real neste ambiente (sem banco disponível aqui) — só verificada
estruturalmente (`alembic heads`); rodar `alembic upgrade head` antes de subir para um ambiente com
dado real.

Não incluído: integração automática de investimento, CAC/ROI por vendedor ou por origem, meta de
receita persistida — todos já listados como fora de escopo no §8.6.
