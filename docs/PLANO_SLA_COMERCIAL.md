# Plano — SLA Comercial em Gestão de Atividades

Status: **proposta, não implementada**. Protótipo funcional em
[`docs/prototypes/sla_comercial_prototype.html`](prototypes/sla_comercial_prototype.html).

## 0. O que já existe (achado na análise)

O projeto **já tem metade do motor de SLA construído**, só que restrito a negócios:

- `PipelineStage.sla_horas` ([`app/models/pipeline.py:51`](../app/models/pipeline.py)) — prazo em
  horas configurável por etapa de pipeline, editável hoje em Configurações > Pipelines
  ([`PipelinesPage.jsx:394`](../frontend/src/pages/PipelinesPage.jsx)).
- `DashboardService._sla_breaches()` ([`app/services/dashboard.py:129`](../app/services/dashboard.py))
  já calcula atraso = `(agora - Deal.ultima_interacao) - stage.sla_horas` e alimenta o card
  "Negócios com SLA estourado" do Dashboard.
- `Deal.ultima_interacao` é uma `column_property` computada a partir do `TimelineEvent` mais
  recente ([`app/models/deal.py:46`](../app/models/deal.py)) — mesmo padrão que o plano da
  Central de Leads propõe replicar para `Company`.

Isso já cobre exatamente o exemplo "**Proposta: follow-up em 48h**" do pedido — é só dar
`sla_horas=48` à etapa "Proposta enviada" em Configurações > Pipelines, hoje. Não precisa de
código novo para esse caso.

O que **não existe** e é o gap real desta feature:

1. SLA amarrado a **status de empresa/lead** (`CompanyStatus`), não só a etapa de negócio —
   cobre "**Novo lead: responder em 24h**". Hoje `Company` não tem nem um timestamp de "desde
   quando está neste status" para medir isso.
2. SLA de **marco único** (não recorrente por etapa) — cobre "**Cliente: primeira reunião em
   7 dias**", que dispara uma vez quando a empresa vira cliente, não a cada mudança de etapa de
   pipeline.
3. **Cumprimento por atividade real**, não só por "tempo parado". O SLA de negócio hoje mede
   silêncio na timeline; o pedido é medir se uma *tarefa do tipo certo foi concluída* dentro do
   prazo — é o que dá sentido a "Gestão de Atividades".
4. Qualquer **visibilidade em Tarefas** — hoje a tela de Tarefas ([`TarefasPage.jsx`](../frontend/src/pages/TarefasPage.jsx))
   não tem noção de prazo comercial, só data/hora que o próprio usuário define.

## 1. Decisões travadas

1. **SLA Comercial mede resposta real, não só tempo parado.** Cumprido = existe uma `Task`
   concluída (ou, na ausência de exigência de tipo, qualquer evento de interação na timeline)
   depois do gatilho e antes do prazo. Ter a tarefa *criada* com vencimento dentro do prazo
   deixa a régua "em andamento"; só *concluída* fecha como cumprida — task vencida e ainda
   pendente é o que gera "estourado".
2. **Três tipos de gatilho, um motor único:**
   - `deal_stage` — **já existe** (`PipelineStage.sla_horas`); esta feature só passa a
     mostrá-lo junto no mesmo painel, sem alterar o cálculo já em produção.
   - `company_status` — novo. Gatilho = `Company.status` muda para um valor com regra ativa.
   - `milestone` — novo. Como `company_status`, mas dispara **uma única vez** por empresa (ex.:
     1ª vez que vira `cliente`), não a cada reentrada no status.
3. **Não bloqueia fluxo.** Mesmo espírito da Central de Leads: SLA estourado gera alerta visual
   (badge, card no Dashboard, filtro em Tarefas), nunca impede salvar, mudar status ou fechar
   negócio. Vendas não fica travada por um contador.
4. **Não cria tarefa automaticamente nesta primeira fase.** O motor só mede e alerta; sugerir/
   criar a tarefa esperada automaticamente ao entrar num estágio é uma extensão natural (fase 2),
   citada em "Fora de escopo".
5. **Regras são dado do tenant, configuráveis, não hardcoded.** Os três exemplos do pedido
   (Lead novo 24h / Proposta 48h / Cliente 1ª reunião 7 dias) nascem como **seed de exemplo**
   editável, não como enum fixo no código — mesmo princípio do ICP scoring e do `sla_horas` de
   pipeline, que já são configuráveis pelo admin.

## 2. Modelo de dados

Tudo aditivo.

### `Company` — novo timestamp
```python
# app/models/company.py
status_atualizado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
```
Gravado em `CompanyService.set_status()` ([`app/services/company.py:100`](../app/services/company.py)),
que já é o único ponto de mudança de status e já registra o evento de timeline "de -> para" — é
só somar `company.status_atualizado_em = datetime.now(timezone.utc)` ali. `NULL` para empresas
existentes (sem backfill, mesmo princípio da Central de Leads); a régua de SLA por
`company_status` simplesmente não se aplica a elas até a próxima mudança de status.

### Nova tabela `activity_sla_rules`
```python
# app/models/activity_sla_rule.py
class SlaGatilhoTipo(str, enum.Enum):
    COMPANY_STATUS = "company_status"
    MILESTONE = "milestone"
    # deal_stage NÃO entra aqui — continua vivendo em PipelineStage.sla_horas,
    # esta tabela só cobre o que falta.

class ActivitySlaRule(Base, TenantMixin, TimestampMixin):
    __tablename__ = "activity_sla_rules"

    id: Mapped[uuid.UUID] = uuid_pk()
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    gatilho_tipo: Mapped[str] = mapped_column(String(20), nullable=False)
    gatilho_valor: Mapped[str] = mapped_column(String(40), nullable=False)  # CompanyStatus.value
    prazo_horas: Mapped[int] = mapped_column(Integer, nullable=False)
    tipo_atividade_esperado: Mapped[str | None] = mapped_column(String(20))  # TaskType.value, opcional
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    ordem: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
```
- `tipo_atividade_esperado` nulo = qualquer tarefa concluída vinculada à empresa conta como
  cumprimento; preenchido (ex. `reuniao`) = só uma tarefa desse tipo conclui a régua.
- `MILESTONE` guarda, por empresa, se já disparou uma vez — tabela auxiliar leve
  `activity_sla_milestone_hits (rule_id, company_id, disparado_em)` para não reprocessar a cada
  troca de status (ex. cliente → inativo → cliente de novo não deveria reabrir o marco).

### Migração Alembic
Uma revisão nova: `ALTER TABLE companies ADD COLUMN status_atualizado_em TIMESTAMPTZ`, mais
`CREATE TABLE activity_sla_rules` e `activity_sla_milestone_hits`, seguindo o padrão de
`fb11856ce211_add_inteligencia_comercial.py`.

## 3. Cálculo do estado de SLA

Novo `app/services/activity_sla.py`, no mesmo espírito de `DashboardService._sla_breaches`:

Para cada empresa ativa com regra `company_status`/`milestone` aplicável:

```
janela_inicio = company.status_atualizado_em  (ou milestone hit)
prazo         = janela_inicio + prazo_horas
cumprida_em   = primeira Task concluída, vinculada à empresa, com
                concluida_em >= janela_inicio e
                (regra.tipo_atividade_esperado is None
                 ou task.tipo == regra.tipo_atividade_esperado)

estado:
  cumprido      → cumprida_em existe e cumprida_em <= prazo
  em_andamento  → não cumprida ainda, falta > 25% do prazo
  em_risco      → não cumprida ainda, falta <= 25% do prazo
  estourado     → não cumprida e agora > prazo
```

Resultado unificado numa única lista, junto com o que `_sla_breaches()` já devolve para
`deal_stage` (sem mexer naquele método) — a UI mostra as três origens lado a lado, mas o cálculo
de `deal_stage` continua exatamente o que já roda em produção hoje.

## 4. Backend — endpoints

- `GET/POST/PATCH/DELETE /configuracoes/sla-regras` — CRUD de `ActivitySlaRule`, mesmo padrão de
  permissão de `PipelinesPage` (gestão/admin).
- `GET /atividades/sla-resumo?apenas_estourado=true` — lista unificada (company_status +
  milestone + deal_stage) com `empresa`, `regra`, `estado`, `prazo`, `horas_restantes` ou
  `horas_atraso`, `responsavel`. Alimenta o painel de Tarefas e o card do Dashboard.
- `Company` ganha campo derivado `sla_status`/`sla_prazo` na resposta de `GET /empresas/{id}`
  (mesmo padrão do `lead_score` proposto na Central de Leads) para o badge no drawer de detalhe.

## 5. Frontend

- **Tarefas** ([`TarefasPage.jsx`](../frontend/src/pages/TarefasPage.jsx)) ganha aba/segmento
  "SLA Comercial" ao lado da lista de tarefas atual:
  - Stat-strip: em dia / em risco / estourado / regras ativas.
  - Painel de cumprimento: empresa, regra disparada, prazo (contagem regressiva ou atraso),
    responsável, atalho "Criar tarefa agora".
  - Tabela de regras (gatilho, prazo, atividade esperada, ativo) com edição inline — mesmo
    componente visual de `StageRow` em Pipelines.
- Badge de SLA (pill colorida: verde/âmbar/vermelho) na lista de tarefas de cada empresa e no
  drawer de detalhe de Empresa/Negócio.
- **Dashboard**: card "SLA Comercial estourado" ao lado do já existente "Negócios com SLA
  estourado" — ou funde os dois num único card com uma coluna de origem (Negócio/Status/Marco),
  a decidir na implementação conforme volume.
- **Configurações > Pipelines**: nenhuma mudança — continua sendo onde `sla_horas` de etapa de
  negócio é editado, sem duplicar essa tela.

## 6. Fora de escopo desta primeira fase

- Sem criação automática de tarefa ao entrar num estágio/status — só mede e alerta. Auto-criar a
  tarefa esperada (reaproveitando o padrão de `proxima_acao_sugerida` do Dossiê Comercial) é
  extensão natural de fase 2.
- Sem notificação por e-mail/Slack de SLA estourado — visibilidade fica dentro do CRM (badges,
  filtros, card de Dashboard) nesta fase.
- Sem gatilho por `funil_estagio` da Central de Leads (ainda não implementada) — o
  `gatilho_tipo` fica desenhado para aceitar um quarto valor (`funil_estagio`) depois, sem
  retrabalho de schema.
- Não altera o cálculo de `deal_stage` já existente (`DashboardService._sla_breaches`) — só
  passa a exibi-lo junto.
- Não altera `CompanyStatus` nem `TaskType` — reaproveita os enums existentes.

## 7. Sequenciamento sugerido

1. Migração (`companies.status_atualizado_em`, `activity_sla_rules`, `activity_sla_milestone_hits`).
2. `CompanyService.set_status` passa a gravar `status_atualizado_em`.
3. `app/services/activity_sla.py` (cálculo) + endpoints CRUD de regras + `sla-resumo`.
4. Seed de regras-exemplo (Lead novo 24h, Cliente → 1ª reunião 7 dias) — editável, não travado.
5. Frontend: aba "SLA Comercial" em Tarefas (regras + painel), badges em Empresas/Negócios,
   card no Dashboard.
6. QA: confirmar que o SLA de `deal_stage` (Proposta 48h) continua idêntico ao de hoje — mudança
   é aditiva, o cálculo existente não é tocado.
