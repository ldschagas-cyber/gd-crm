# Plano — Previsão Comercial (Forecast/Commit) e integração com Metas do Funil

Status: **implementado** (backend + frontend, vertical slice completa — ver §7). Protótipo
funcional em [`docs/prototypes/previsao_comercial_prototype.html`](prototypes/previsao_comercial_prototype.html)
(inclui a página Previsão Comercial e a integração visual com Metas do Funil, navegáveis no
mesmo arquivo).

## 0. Contexto

Pedido: cobrir o item "Forecast" do quadro de Pipeline Comercial — receita prevista,
probabilidade, data de fechamento, pipeline por vendedor e "commit" — e avaliar se esse
processo se encaixa no que já existe em Metas do Funil ([`PLANO_METAS_FUNIL.md`](PLANO_METAS_FUNIL.md)).

## 1. Análise de viabilidade

**Quase tudo já existia.** `Deal` já tinha `valor_previsto`, `probabilidade`,
`data_prev_fechamento` e `responsavel_id` — o cálculo de forecast ponderado
(`valor × probabilidade / 100`) já roda hoje por etapa no Kanban
([`NegociosPage.jsx`](../frontend/src/pages/NegociosPage.jsx), coluna "Valor ponderado" do board).
O único conceito novo é **Commit**: um sinalizador manual, por negócio, com que o vendedor
assume "esse fecha esse mês" — distinto da probabilidade ponderada (que é inferida da etapa,
não uma promessa).

**Modelo adotado**: `Deal.commit: bool`, default `False`, editável pelo vendedor no board, na
ficha do negócio e na própria tela de Previsão Comercial. Sem tabela nova.

## 2. Fórmulas

Para um conjunto de negócios abertos com `data_prev_fechamento` dentro do mês selecionado:

- **Pipeline** = Σ `valor_previsto`
- **Forecast** = Σ `valor_previsto × probabilidade / 100` — mesma fórmula já usada no rodapé
  de cada coluna do Kanban, agora agregada por mês/vendedor em vez de por etapa.
- **Commit** = Σ `valor_previsto` apenas dos negócios com `commit = true`

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
   por vendedor do Commit/Forecast é essa extensão, chegando pela porta da receita.
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
  (Pipeline/Forecast/Commit), tabela por vendedor, lista de negócios do mês com checkbox de
  Commit editável ali mesmo.
- Checkbox de Commit também no board de Negócios (ícone de estrela no card do Kanban e na
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
