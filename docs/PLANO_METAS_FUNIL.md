# Plano — Metas do Funil Comercial (controle de fase por percentual)

Status: **implementado** (backend + frontend, vertical slice completa — ver §11). Protótipo
funcional original em
[`docs/prototypes/metas_funil_prototype.html`](prototypes/metas_funil_prototype.html).

## 0. Contexto

A operação comercial da GD Conecta segue um funil de 7 etapas, do topo (empresa pesquisada) ao
fechamento (cliente), com meta absoluta por etapa e uma meta de conversão (% da etapa anterior)
definida a partir de benchmark de mercado B2B consultivo. Hoje esse funil vive numa planilha/anexo
— o pedido é avaliar se vale a pena trazê-lo pro CRM como um controle de verdade, e como.

O funil cruza três domínios que já existem e não se falam hoje: `LeadProspect` (Pesquisa de
Leads, pré-CRM), a Central de Leads (`Company.funil_estagio`) e `Deal`/`PipelineStage` (Negócios).
Ver [`docs/PLANO_CENTRAL_DE_LEADS.md`](PLANO_CENTRAL_DE_LEADS.md) para o funil que já existe entre
promoção e conversão em negócio — este plano é complementar, não substitui aquele.

## 1. Análise de viabilidade

**Recomendação: sim, vale a pena — e é barato.** Nenhum dos 7 números do Anexo 1 exige uma
tabela nova para ser *contado*; todos já nascem de eventos que o sistema grava hoje
(`LeadProspect`, `TimelineEvent`, `Deal`). O que falta é só um lugar para guardar a *meta* e um
serviço que some o que já existe. Isso muda a natureza do trabalho de "novo domínio" para
"relatório sobre domínios existentes" — mesmo padrão de `resumo_central_leads` e
`performance_report`, que já fazem exatamente isso para outros recortes.

**Ganho real para a operação**, não só "ter um dashboard a mais":
- O Playbook de Outbound já instrui *"ajuste o ritmo depois de medir taxa de resposta/reunião...
  não abra mais volume até validar a taxa de conversão de cada etapa"* — hoje isso depende de
  alguém abrir uma planilha e calcular na mão. O controle por percentual torna essa regra visível
  e automática a cada período, em vez de conhecimento tácito.
- Detecta cedo qual etapa está estrangulando o funil (ver §2 — a leitura do próprio Anexo 1 já
  aponta contato→reunião como a meta mais agressiva frente ao mercado; é exatamente o tipo de
  sinal que se perde numa planilha atualizada esporadicamente).
- Dá munição objetiva para decidir "abrir mais volume de prospecção" vs. "corrigir critério de
  qualificação/cadência antes de escalar" — a alternativa que o usuário já identificou como a
  leitura certa quando a taxa vem abaixo do esperado.

**Custo/risco de implementação:**
- Baixo para a contagem (dados já existem — ver mapeamento em §3).
- Médio para dois pontos que precisam de decisão de produto, não só engenharia:
  1. **Janela temporal**: coorte (as 300 pesquisadas em agosto, quantas delas viraram reunião,
     mesmo que em setembro?) vs. atividade do período (quantas reuniões aconteceram em agosto,
     não importa quando a empresa foi pesquisada). São números diferentes e ambos válidos — ver
     §4. Recomendo **coorte** como leitura principal (é o que o Anexo 1 realmente descreve — um
     funil de uma leva), com atividade-do-mês como métrica auxiliar mais fácil de calcular.
  2. **"Decisor identificado" não tem um campo dedicado hoje** — a proposta usa
     `LeadProspect.contato_sugerido` (preenchido) como proxy. Funciona para o MVP; se a
     qualidade do dado nesse campo for ruim na prática, vale promover para um status explícito
     depois (fora de escopo aqui).
- **Não recomendo bloquear transições individuais** com base nisso — conflitaria com a decisão já
  travada na Central de Leads de que `mql→sql` e toda promoção de estágio são sempre manuais (ver
  [`PLANO_CENTRAL_DE_LEADS.md` §0.1](PLANO_CENTRAL_DE_LEADS.md)). O controle certo aqui é
  **monitoramento com alerta**, não gate de fluxo — ver §6.

## 2. Anexo 1 — detalhamento dos percentuais

| # | Etapa | Meta | % da etapa anterior | % acumulado desde o topo | Referência de mercado (B2B consultivo, ticket alto) |
|---|---|---:|---:|---:|---|
| 1 | Empresas pesquisadas | 300 | — | 100% | Base de prospecção (topo) |
| 2 | Decisores identificados | 100 | 33% | 33,3% | 30–50% é comum em prospecção ativa com ICP bem definido |
| 3 | Contatos realizados | 50 | 50% | 16,7% | 40–60% dos decisores mapeados costumam ser efetivamente contatados |
| 4 | Reuniões marcadas | 30 | 60% | 10,0% | 17–31% é a média nacional contato→oportunidade (outbound: ~17%); meta interna está acima da média |
| 5 | Diagnósticos realizados | 20 | 67% | 6,7% | Sem benchmark direto — etapa específica do modelo GD; alinhada à faixa saudável de 20–40% por etapa em B2B consultivo |
| 6 | Propostas enviadas | 15 | 75% | 5,0% | Alinhada à faixa saudável de 20–40% por etapa em B2B consultivo |
| 7 | Clientes fechados | 10 | 67% | 3,3% | 6–10% é a média de fechamento (SQL→cliente) em consultorias e serviços profissionais no funil completo; meta interna está bem acima |

**Leitura:** as metas internas são mais agressivas que a média de mercado em praticamente todas as
etapas — especialmente contato→reunião (60% vs. 17–31% nacional) e o fechamento final (67% vs.
6–10% em consultorias). Coerente com um modelo de prospecção altamente qualificada (poucas
empresas, rigorosamente filtradas pelo ICP e pelo critério de passagem da seção 1.0.1 da
especificação) em vez de alto volume com baixa qualificação. Recomenda-se monitorar de perto nos
primeiros meses reais de operação: taxas muito abaixo do projetado são sinal de ajustar critério
de qualificação ou execução da cadência — não necessariamente de que a meta esteja errada. **Essa
frase é literalmente a regra de negócio que a seção 6 abaixo transforma em alerta do sistema.**

## 3. Mapeamento das etapas para dados que já existem

Nenhuma etapa exige um domínio novo — todas se apoiam em campos/eventos já gravados hoje:

| Etapa | Fonte no CRM | Cálculo (MVP) |
|---|---|---|
| Empresas pesquisadas | `LeadProspect` | `COUNT(LeadProspect criados no período)` |
| Decisores identificados | `LeadProspect.contato_sugerido` | `COUNT(... WHERE contato_sugerido IS NOT NULL)` — proxy já existente, ver §1 |
| Contatos realizados | `Company` promovida + `TimelineEvent` | `COUNT(Company via promoted_company_id COM ≥1 TimelineEvent tipo ligacao/email)` |
| Reuniões marcadas | `TimelineEvent.tipo = 'reuniao'` | `COUNT(DISTINCT company_id)` com evento tipo reunião no período — enum já existe em [`app/models/timeline.py`](../app/models/timeline.py) |
| Diagnósticos realizados | `Deal` que atingiu a etapa de Diagnóstico | `COUNT(DISTINCT deal)` — via primeiro `TimelineEvent tipo=pipeline` cujo `meta.para` aponta pra uma `PipelineStage` marcada como diagnóstico (ver §5) |
| Propostas enviadas | `Deal` que atingiu a etapa de Proposta | mesmo mecanismo, etapa proposta |
| Clientes fechados | `Deal.status = 'ganho'` | `COUNT(Deal WHERE status='ganho' no período)` |

Ponto de atenção: as etapas 5 e 6 hoje só são identificáveis por **nome** da `PipelineStage`
(`"Diagnóstico"`, `"Proposta"` — livres, editáveis por tenant, ver
[`pipeline_prototype.html`](prototypes/pipeline_prototype.html)). Casar por nome é frágil (basta
renomear a etapa no Pipeline e a métrica quebra silenciosamente). Por isso a §5 propõe uma tag
explícita (`marco_funil`) na etapa, em vez de comparar string.

Toda mudança de estágio de `Deal` já grava `TimelineEvent tipo='pipeline'` com `meta={"de", "para"}`
([`app/services/deal.py:116`](../app/services/deal.py)) — é o que permite reconstruir "quando esse
negócio *primeiro* passou pela etapa X", em vez de só saber onde ele está agora. Sem isso o cálculo
de coorte (§1) não seria possível sem nova tabela.

## 4. Coorte vs. atividade do período

- **Coorte (recomendado como leitura principal)**: fixa o conjunto de `LeadProspect` criados no
  período de referência (ex.: agosto/2026) e mede, para *essas mesmas empresas*, quantas
  avançaram até cada marco — não importa em que mês o marco aconteceu. É o que o Anexo 1
  realmente descreve (uma leva de 300 vira, no fim, 10 clientes). Efeito colateral esperado e
  saudável: coortes recentes (última semana/mês) vão aparecer com números baixos nas últimas
  etapas simplesmente porque o ciclo ainda não correu — a tela deve deixar isso explícito (ex.:
  "coorte com 12 dias — etapas de fechamento ainda em andamento"), não tratar como alerta.
- **Atividade do período (métrica auxiliar)**: conta eventos que aconteceram no mês, não importa
  a origem — "quantas reuniões marcadas em agosto", igual ao que
  [`DesempenhoPesquisaPage`](../frontend/src/pages/DesempenhoPesquisaPage.jsx) já faz para volume
  de pesquisa. Mais simples de calcular, mais estável mês a mês, mas mistura leads de origens
  diferentes — não é o "funil de uma leva" do Anexo 1.

Proposta: implementar os dois, com um toggle na tela (o protótipo já simula essa alternância),
coorte como padrão.

## 5. Modelo de dados (aditivo, sem migração de dado histórico)

Nenhuma tabela nova. Dois acréscimos, mesmo padrão de campos opcionais já usado no projeto
(`PipelineStage.probabilidade`, `tenants.config.icp_scoring_rules`):

```python
# app/models/pipeline.py — PipelineStage
class FunilMarco(str, enum.Enum):
    REUNIAO = "reuniao"
    DIAGNOSTICO = "diagnostico"
    PROPOSTA = "proposta"

marco_funil: Mapped[str | None] = mapped_column(String(20))
```
`None` por padrão — só as etapas que o gestor apontar como "esta é a etapa de Diagnóstico do meu
funil de metas" ganham a tag, via um seletor na tela de configuração do Pipeline
([`PipelinesPage.jsx`](../frontend/src/pages/PipelinesPage.jsx)). Resolve o problema de casar por
nome (§3) e sobrevive a rename de etapa.

```json
// tenants.config.funil_metas — mesmo container já usado por icp_scoring_rules
{
  "empresas_pesquisadas_meta": 300,
  "etapas": [
    {"chave": "decisores",     "pct_etapa_anterior": 33},
    {"chave": "contatos",      "pct_etapa_anterior": 50},
    {"chave": "reunioes",      "pct_etapa_anterior": 60},
    {"chave": "diagnosticos",  "pct_etapa_anterior": 67},
    {"chave": "propostas",     "pct_etapa_anterior": 75},
    {"chave": "fechados",      "pct_etapa_anterior": 67}
  ]
}
```
A meta absoluta de cada etapa é sempre derivada em cascata a partir de
`empresas_pesquisadas_meta` e dos percentuais — não se grava número absoluto por etapa (evita os
dois ficarem inconsistentes entre si). O protótipo já implementa esse recálculo em cascata ao
editar qualquer percentual.

## 6. Regras do "controle" — monitorar, não bloquear

Consistente com a decisão já travada de que transições de estágio continuam manuais e sob
julgamento do vendedor: este controle **não impede** ninguém de marcar uma reunião, promover um
lead ou avançar um negócio. Ele:

1. Calcula, por etapa, `real % da etapa anterior` vs. `meta % da etapa anterior`.
2. Classifica em 3 faixas (mesmo padrão de cor já usado em `qualClass`/`statusColor` no restante
   do produto): dentro de ~5 p.p. da meta = ok; 5–15 p.p. abaixo = atenção; mais de 15 p.p. abaixo
   = crítico.
3. Quando uma etapa fica crítica por 2 períodos seguidos, gera o alerta de leitura que o próprio
   usuário já escreveu: *"taxa muito abaixo do projetado — revisar critério de qualificação ou
   execução da cadência antes de abrir mais volume"*, na etapa específica que estrangulou.

Bloqueio automático de volume (ex.: impedir novas buscas em massa em Pesquisa de Leads enquanto o
funil estiver crítico) fica deliberadamente **fora do MVP** — é um gate real, de maior impacto e
mais fácil de errar; se depois de usar o monitor por um tempo fizer sentido, entra como extensão
separada, com decisão explícita de quem pode destravar.

## 7. Backend — endpoints propostos

Reaproveita os serviços que já existem (`LeadProspectService`, `CompanyService`, `DealService`) —
sem novo domínio, mesmo espírito do endpoint de resumo da Central de Leads:

- `GET /funil-metas/resumo?modo=coorte|atividade&periodo=2026-08` — os 7 números reais + as metas
  já resolvidas em cascata + status por etapa.
- `GET/PUT /tenant/funil-metas` — config do §5 (admin/gestor), mesmo formato de
  `GET/PUT /tenant/lead-score-rules` que já existe.
- `PATCH /pipelines/{id}/stages/{stage_id}` — extensão aditiva pra aceitar `marco_funil` (rota já
  existe em [`app/api/v1/pipelines.py`](../app/api/v1/pipelines.py)).

## 8. Frontend

- Nova seção "Metas do Funil" — o protótipo entregue (§ arquivo no topo) já assume que ela vive
  dentro de **Indicadores & Metas** (grupo "Inteligência Comercial" do menu, ao lado de Central de
  Leads), reaproveitando os componentes visuais que essa tela já definiu (`goal-card`, `.funnel`,
  `status-pill`, painel lateral "Editar metas").
- Toggle Coorte/Atividade do mês, seletor de período (mesmo padrão de mês do
  `DesempenhoPesquisaPage`).
- Tabela do Anexo 1 completa (meta, % etapa anterior, real, diferença em p.p., referência de
  mercado, status) — visível na própria tela, não só num documento à parte.
- Painel "Editar metas do funil": edita a meta de empresas pesquisadas e o % esperado de cada
  etapa; a cascata de metas absolutas recalcula ao vivo.

## 9. Fora de escopo desta primeira fase

- Bloqueio/gate de volume (§6).
- Status explícito de "decisor identificado" no `LeadProspect` (usa proxy por enquanto, §1).
- Séries históricas/gráfico de tendência mês a mês — a §7 devolve o período consultado, não uma
  série; comparar meses fica pra quando houver mais de 2-3 meses de dado real pra olhar.
- Metas por vendedor/pipeline individual — o Anexo 1 é uma meta de operação como um todo; segmentar
  por responsável é extensão natural, não bloqueante.

## 10. Sequenciamento sugerido

1. `PipelineStage.marco_funil` (migração aditiva) + seletor na configuração do Pipeline.
2. `tenants.config.funil_metas` (schema + endpoint `GET/PUT`).
3. Serviço de resumo (`GET /funil-metas/resumo`), modo atividade primeiro (mais simples), coorte
   depois.
4. Frontend: tela dentro de Indicadores & Metas, a partir do protótipo já validado.
5. QA: conferir que nada em Pipeline/Negócios muda de comportamento (campo novo é opcional e não
   lido em nenhum outro lugar).

## 11. Implementação — o que foi entregue

Backend: migração [`5beda113fc7b`](../alembic/versions/5beda113fc7b_add_marco_funil_to_pipeline_stages.py)
(`pipeline_stages.marco_funil`); `FunilMarco` em
[`app/models/pipeline.py`](../app/models/pipeline.py); seletor de marco em `StageCreate`/`StageRead`
([`app/schemas/pipeline.py`](../app/schemas/pipeline.py)) e em `PipelineService.add_stage/update_stage`;
[`app/services/funil_metas.py`](../app/services/funil_metas.py) novo (`FunilMetasService` —
`get_config`/`update_config`/`resumo`, os dois modos coorte e atividade implementados, não só o
MVP de atividade sugerido no §10); endpoints `GET /funil-metas/resumo` e
`GET/PUT /tenant/funil-metas`. Ajuste em `DealService.create` ([`app/services/deal.py`](../app/services/deal.py)):
o evento de criação do negócio passou a gravar `meta={"para": stage_id}`, no mesmo formato de
`move_stage` — sem essa uniformização, negócios criados direto numa etapa marcada não seriam
contados como "já passaram por ela" na leitura de coorte.

Frontend: [`FunilMetasPage.jsx`](../frontend/src/pages/FunilMetasPage.jsx) novo — funil visual
meta-vs-real, tabela completa do Anexo 1, alerta automático na etapa mais crítica, painel "Editar
metas" com cascata ao vivo, toggle Coorte/Atividade — + item de menu "Metas do Funil" (grupo
Inteligência Comercial) e rota `/metas-funil`; seletor de marco do funil (Diagnóstico/Proposta)
adicionado à configuração de etapas em [`PipelinesPage.jsx`](../frontend/src/pages/PipelinesPage.jsx).

**Desvio em relação ao §9 original:** a tela não vive "dentro de Indicadores & Metas" — essa tela
nunca chegou a ser implementada de verdade (só existe como protótipo solto,
`docs/prototypes/indicadores_metas_prototype.html`; nenhuma rota real usa esse nome). Metas do
Funil ganhou rota própria (`/metas-funil`), mesmo padrão usado quando Central de Leads foi
adicionada como página nova.

Verificado: `pytest` (28 passed, incluindo os 9 testes novos de `_periodo_bounds`/`_montar_resumo`
em [`tests/test_funil_metas.py`](../tests/test_funil_metas.py)), `alembic heads` (head único,
cadeia linear), `vite build` (bundle ok), import completo do FastAPI app + geração do schema
OpenAPI confirmando as 3 rotas novas registradas sem conflito.

Não incluído nesta entrega: bloqueio/gate de volume (§6 — deliberadamente fora), status explícito
de "decisor identificado" (usa o proxy `contato_sugerido`, §1), séries históricas/gráfico de
tendência mês a mês, metas por vendedor/pipeline individual (todos já listados como fora de escopo
no §9). A migração não foi executada contra um Postgres real neste ambiente (sem banco disponível
aqui) — só verificada estruturalmente (`alembic heads`); rodar `alembic upgrade head` antes de
subir para um ambiente com dado real.
