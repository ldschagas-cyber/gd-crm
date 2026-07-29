# Especificação Técnica — CRM GD Conecta

**Versão:** 1.0 · **Base:** Documento de Requisitos "CRM GD Conecta — Versão 1.0" · **Autor:** Arquitetura (assistida por IA) · **Escopo:** análise de viabilidade + especificação técnica para desenvolvimento. Nenhum requisito de negócio foi alterado; onde a especificação técnica precisa de uma decisão que o documento funcional não define, isso é sinalizado explicitamente como **"a validar com o PO"**.

> **Nota metodológica:** o repositório `C:\gdconecta\crm` já contém um backend funcional (não é greenfield). Esta especificação documenta o que **já existe** (para não ser redesenhado sem motivo) e projeta o que **falta construir** para atender integralmente ao documento de requisitos. Diretório ainda não é um repositório Git — recomenda-se `git init` antes de iniciar qualquer nova frente de trabalho.
>
> **Atualização de 2026-07-27:** uma rodada de prototipagem de frontend (13 telas em artifacts interativos) revelou decisões de produto e módulos novos não previstos no documento de requisitos original. Todos estão consolidados na **seção 9** — leia-a antes de iniciar a Fase 1/2, pois ela altera premissas de seções anteriores (ex.: o CRM é de **uso interno**, não SaaS comercializável; a integração de e-mail alvo é **Microsoft 365/Graph**, não Gmail/Outlook genérico).

---

## 0. Sumário Executivo — Análise de Viabilidade

### 0.1 Estado atual (as-is)

| Camada | Situação | Cobertura vs. requisitos |
|---|---|---|
| **Backend** (FastAPI) | Implementado, rodando, com arquitetura em camadas limpa | RF001–RF009, RF012–RF014 ~90% prontos. RF019/RF020 parcialmente (worker existe, endpoint de upload não). RF021 ausente. RF024 parcial (CRUD sim, IA/Sequências/Workflows não). |
| **Banco de dados** | PostgreSQL 16 + Alembic, 1 migração inicial, RLS habilitado | Cobre 100% das entidades do MVP (seção 10 do doc de requisitos) |
| **Multi-tenant** | Implementado em 3 camadas (JWT → contexto → RLS) | RF002 e RNF001 atendidos na base do MVP |
| **Frontend** | **Não existe nenhum código** (sem diretório `frontend/`) | RF001–RF024 sem interface — 0% |
| **Automações (Fase 2)** | Backend 0%. **Frontend: UI prototipada e aprovada** (Sequências, Cadências, Workflows, Modelos de e-mail — ver §9.5) | RF010, RF011, RF018 — 0% no backend |
| **IA / Enriquecimento (Fase 3)** | Não iniciado (sem chaves de API, sem módulo) | RF015, RF016, RF017 — 0% |
| **Testes automatizados** | Inexistentes (sem `pytest` no `requirements.txt`, sem pasta `tests/`) | RNF (qualidade) não atendido |
| **CI/CD, observabilidade, backups** | Inexistentes | RNF002, RNF007 parcialmente em risco |

**Veredito de viabilidade: alta.** A base arquitetural é sólida e segue boas práticas (isolamento por tenant em profundidade, JWT sem confiar em payload do cliente, camadas bem separadas, RLS como defesa adicional). O maior volume de trabalho restante não é "risco técnico", é **volume de escopo ainda não iniciado** — principalmente o frontend inteiro e as Fases 2–3. Recomenda-se seguir construindo sobre o que já existe, sem reescrever o backend do MVP.

### 0.2 Gaps identificados (para priorização)

| # | Gap | Severidade | Observação |
|---|---|---|---|
| G1 | Frontend inexistente | Alta | Maior item de esforço restante; nenhuma tela pode ser demonstrada hoje |
| G2 | Upload de importação (RF019/RF020) sem endpoint | Média | `import_companies_task`/`import_contacts_task` (Celery) existem e funcionam, mas nenhuma rota HTTP dispara ou consulta o job |
| G3 | Exportação (RF021) não implementada | Média | Nenhum endpoint de export em Excel/CSV/PDF |
| G4 | Recuperação de senha incompleta | Média | `forgot-password` gera token de reset mas **não envia e-mail** (não há integração SMTP/provedor) — o fluxo é inutilizável fim-a-fim hoje |
| G5 | RBAC por perfil aplicado de forma parcial | Média | `Visualizador` tem, hoje, as mesmas permissões de escrita que `Vendedor` na maioria dos endpoints (Empresas, Contatos, Negócios, Tarefas só exigem usuário autenticado, não checam perfil) |
| G6 | Sem escopo de visibilidade por vendedor | Baixa/Média | Todo usuário autenticado lista todas as empresas/negócios do tenant; não há filtro automático "vendedor só vê o que é seu" — **a validar com o PO** se é o comportamento desejado |
| G7 | Sem testes automatizados nem CI | Alta (risco de regressão) | Nenhum `tests/`, nenhum workflow de CI encontrado |
| G8 | Sem observabilidade/logging estruturado | Média | RNF002 pede log de todas as operações; hoje só há `audit_logs` para CRUD, sem logging de aplicação/APM |
| G9 | `SECRET_KEY` placeholder em `.env` | Alta (segurança) | Precisa ser rotacionado antes de qualquer ambiente não-local |
| G10 | Sem armazenamento de objetos (arquivos) | Média | `ImportJob.arquivo` é `String`, mas não há bucket/S3/MinIO definido para guardar o arquivo enviado |
| G11 | Sem integração de IA configurada | Baixa (é Fase 3) | Sem chaves OpenAI/Claude em `config.py`; esperado, pois é fora do MVP |
| G12 | Sem scheduler (Celery Beat) | Média | Necessário para Sequências (RF010) e Cadências (RF011), que dependem de disparos por dia decorrido |

### 0.3 Recomendação de sequenciamento

1. Fechar o MVP (RF001–RF014, RF019–RF021) no backend (G2, G3, G4, G5) — esforço pequeno, reaproveita tudo que já existe.
2. Construir o frontend do MVP (G1) — maior esforço, mas sem dependências externas.
3. Testes + CI mínimos (G7) antes de abrir Fase 2, para não acumular dívida técnica.
4. Fase 2 (Sequências, Cadências, Workflows) — depende de integração de e-mail (**Microsoft 365/Graph**, não Gmail/Outlook genérico — ver §9.2) para o requisito "pausar sequência quando houver resposta" (RF010). UI já prototipada e aprovada (§9.5).
5. Fase 3 (IA, Enriquecimento) — o item "SaaS self-service" desta fase fica **deprioritizado**: o CRM é de uso interno da GD Conecta, não será comercializado a princípio (§9.0).

---

## 1. Arquitetura do Sistema

### 1.1 Visão geral

```
┌─────────────┐      HTTPS       ┌──────────────┐      ┌────────────────────┐
│  Frontend    │ ───────────────▶│    Nginx     │─────▶│   FastAPI (api)    │
│  React SPA   │◀─────────────── │ (reverse     │      │  router→service→   │
│  (a construir)│                 │  proxy +     │      │  repository→model  │
└─────────────┘                  │  estáticos)  │      └─────────┬──────────┘
                                  └──────────────┘                │
                                                                  ▼
                                              ┌───────────────────────────────┐
                                              │  PostgreSQL 16 (RLS por tenant)│
                                              └───────────────────────────────┘
                                                                  ▲
                                              ┌───────────────────┴───────────┐
                                              │   Redis (broker + result)     │
                                              └───────────────────┬───────────┘
                                                                  ▼
                                              ┌───────────────────────────────┐
                                              │  Celery worker (+ Beat, a criar)│
                                              │  import, cadências, IA, etc.   │
                                              └───────────────────────────────┘
```

### 1.2 Backend — já implementado

- **Python 3.12**, **FastAPI 0.115**, **SQLAlchemy 2.0** (mapeamento declarativo tipado com `Mapped`), **Alembic 1.14**, **Pydantic v2**, **PyJWT**, **passlib/bcrypt**, **Celery 5.4** + **Redis**, **pandas/openpyxl** (import Excel/CSV).
- Arquitetura em camadas estrita: `api/` (HTTP, sem regra de negócio) → `schemas/` (DTOs Pydantic) → `services/` (regra de negócio/transação) → `repositories/` (acesso a dados, tenant automático) → `models/` (ORM + mixins).
- Documentação automática via Swagger (`/docs`) e OpenAPI (`/api/v1/openapi.json`) — atende RF024/RNF005.

**A adicionar no backend (fora de módulos novos de domínio):**
- Camada de envio de e-mail (SMTP genérico ou provedor tipo SES/SendGrid) — necessária tanto para reset de senha quanto para Cadências (RF011).
- Camada de abstração de provedor de IA (`app/services/ai/`) com adaptadores para OpenAI e Claude, selecionável por configuração — necessária para RF015–RF017.
- Celery Beat (agendador) para disparos baseados em tempo (Sequências, Cadências, SLA de pipeline).
- Camada de storage de arquivos (local em dev, S3/MinIO compatível em produção) para anexos de importação e, futuramente, anexos de negócios/e-mails.
- Suite de testes (`pytest` + `pytest-asyncio`/`httpx` para testes de API, fixtures de tenant/RLS).

### 1.3 Frontend — a construir integralmente

Stack definida no documento de requisitos: **React 18 + TypeScript + Material UI (MUI) + React Query + React Router**. Nenhum código existe ainda. Ver seção 5 para estrutura detalhada.

Recomendação de tema: aplicar a identidade visual oficial já definida para a marca GD Conecta (Índigo `#2D3561`, Âmbar `#C9A84C`, Azul `#0077A8`, Marfim `#F5F1EB`, tipografia IBM Plex Sans/Mono) no tema do MUI (`createTheme`), já que este CRM é um produto da própria GD Conecta — evita retrabalho de rebranding depois.

### 1.4 Banco de dados

- **PostgreSQL 16** (via `postgres:16-alpine` no `docker-compose.yml`).
- Migrações gerenciadas por Alembic, com o metadata dos models como fonte única de verdade (`Base.metadata.create_all` dentro da migração — abordagem incomum mas documentada e intencional: evita divergência model↔schema no início do projeto). **Atenção:** a partir da 2ª migração, o padrão deve mudar para `alembic revision --autogenerate`, senão a "fonte única" quebra a rastreabilidade histórica do schema.
- Row-Level Security (RLS) habilitada e **forçada** (`FORCE ROW LEVEL SECURITY`) nas tabelas multi-tenant.

### 1.5 Infraestrutura

**Já existe** (`docker-compose.yml`): `db` (Postgres), `redis`, `api` (Uvicorn + reload), `worker` (Celery), `nginx` (proxy reverso, hoje só expõe `/api/`, `/docs`, `/openapi.json`, `/health`).

**Falta para produção/SaaS:**
- Serviço `frontend` no compose (build estático servido pelo Nginx, ou container Node/Vite dedicado).
- Celery Beat como serviço próprio (`worker-beat`).
- Object storage (MinIO em dev / S3 em produção).
- Gestão de segredos fora do `.env` versionável (Docker secrets, Vault, ou variáveis de ambiente do orquestrador em produção).
- Pipeline de CI/CD (lint, testes, build de imagem, migração automática em deploy).
- Observabilidade: logging estruturado (JSON) + agregador (ex.: Loki/ELK) e métricas (Prometheus) — hoje só há `echo=settings.DEBUG` do SQLAlchemy.
- Backup automatizado do Postgres (pg_dump agendado ou WAL archiving) — crítico dado RNF008 (100k+ empresas por tenant).
- Ambientes segregados (dev/staging/produção) com `.env` por ambiente e banco de dados isolado.

---

## 2. Modelo de Dados

### 2.1 Tabelas já implementadas (migração `0001_initial`)

Todas as tabelas abaixo (exceto `tenants`) têm `tenant_id UUID NOT NULL` (mixin `TenantMixin`), `created_at`/`updated_at` (mixin `TimestampMixin`) e RLS habilitada. PK padrão é `id UUID` (default `uuid4()`).

#### `tenants`
| Campo | Tipo | Notas |
|---|---|---|
| id | UUID (PK) | |
| razao_social | String(255) NOT NULL | |
| nome_fantasia | String(255) | |
| cnpj | String(14) UNIQUE NOT NULL | |
| plano | String(40) NOT NULL default `starter` | |
| status | String(20) NOT NULL default `ativo` | enum: ativo/suspenso/cancelado |
| config | JSONB | configurações independentes por empresa (RF002) |

#### `users`
| Campo | Tipo | Notas |
|---|---|---|
| id | UUID (PK) | |
| tenant_id | UUID (FK tenants) | |
| nome | String(255) NOT NULL | |
| email | String(255) NOT NULL, index | único **por tenant** (`uq_user_tenant_email`) |
| senha_hash | String(255) NOT NULL | bcrypt |
| telefone | String(20) | |
| cargo | String(120) | |
| perfil | String(30) NOT NULL default `vendedor` | enum: admin/gestor/vendedor/visualizador |
| status | String(20) NOT NULL default `ativo` | enum: ativo/inativo |
| ultimo_acesso | DateTime(tz) | |

#### `companies`
| Campo | Tipo | Notas |
|---|---|---|
| id | UUID (PK) | |
| tenant_id | UUID (FK) | índice composto `(tenant_id, status)` |
| razao_social | String(255) NOT NULL, index | |
| nome_fantasia | String(255) | |
| cnpj | String(14) | único **por tenant** (`uq_company_tenant_cnpj`) |
| site, telefone, email | String | |
| endereco, cidade | String(255)/(120) | |
| uf | String(2) | |
| segmento, porte | String | |
| num_funcionarios | Integer | |
| faturamento_estimado | Numeric(15,2) | |
| status | String(20) NOT NULL default `lead`, index | enum: lead/qualificado/cliente/perdido/inativo |
| origem | String(80) | origem do lead |
| responsavel_id | UUID (FK users) | |
| created_by | UUID (FK users) | |
| deleted_at | DateTime(tz) nullable | soft delete |

#### `contacts`
| Campo | Tipo | Notas |
|---|---|---|
| id | UUID (PK) | |
| tenant_id | UUID (FK) | |
| company_id | UUID (FK companies) NOT NULL, index | multi-contato por empresa (RF006) |
| nome | String(255) NOT NULL | |
| cargo, email, telefone, whatsapp, linkedin | String | |
| data_nascimento | Date | |
| observacoes | Text | |

#### `pipelines`
| Campo | Tipo | Notas |
|---|---|---|
| id | UUID (PK) | |
| tenant_id | UUID (FK) | |
| nome | String(120) NOT NULL | |
| is_default | Boolean default false | |
| ativo | Boolean default true | |
| cor_exibicao | String(20) default `sem_cor` | enum: `sem_cor`/`ponto`/`selo` — como o nome da etapa aparece no board/lista de Negócios (migração `d224b580a440`, 2026-07-28) |

#### `pipeline_stages`
| Campo | Tipo | Notas |
|---|---|---|
| id | UUID (PK) | |
| tenant_id | UUID (FK) | |
| pipeline_id | UUID (FK pipelines) NOT NULL, index | `cascade="all, delete-orphan"` a partir do pipeline |
| nome | String(120) NOT NULL | |
| ordem | Integer default 0 | ordena etapas no board |
| tipo | String(20) default `aberta` | enum: aberta/ganho/perdido |
| sla_horas | Integer nullable | RF008 — controle de SLA por etapa |
| probabilidade | Integer nullable | usado como default ao mover negócio p/ etapa |

#### `deals`
| Campo | Tipo | Notas |
|---|---|---|
| id | UUID (PK) | |
| tenant_id | UUID (FK) | índices `(tenant_id, stage_id)` e `(tenant_id, responsavel_id)` |
| nome | String(255) NOT NULL | |
| company_id | UUID (FK companies) NOT NULL, index | |
| contact_id | UUID (FK contacts) nullable | contato principal |
| responsavel_id | UUID (FK users) NOT NULL, index | |
| pipeline_id | UUID (FK pipelines) NOT NULL | |
| stage_id | UUID (FK pipeline_stages) NOT NULL, index | |
| valor_previsto | Numeric(15,2) | |
| probabilidade | Integer | |
| data_prev_fechamento | Date | |
| origem | String(80) | |
| status | String(20) default `aberto`, index | enum: aberto/ganho/perdido |
| motivo_perda | String(255) | |
| data_fechamento | DateTime(tz) | |

#### `tasks`
| Campo | Tipo | Notas |
|---|---|---|
| id | UUID (PK) | |
| tenant_id | UUID (FK) | índice `(tenant_id, responsavel_id, status)` |
| titulo | String(255) NOT NULL | |
| tipo | String(20) NOT NULL | enum: ligacao/email/whatsapp/reuniao/followup |
| responsavel_id | UUID (FK users) NOT NULL, index | |
| company_id, contact_id, deal_id | UUID (FK) nullable | vínculo opcional |
| data | Date NOT NULL, index | |
| hora | Time nullable | |
| prioridade | String(20) default `media` | enum: baixa/media/alta |
| status | String(20) default `pendente`, index | enum: pendente/concluida/cancelada |
| concluida_em | DateTime(tz) | |

#### `timeline_events`
| Campo | Tipo | Notas |
|---|---|---|
| id | UUID (PK) | |
| tenant_id | UUID (FK) | índice `(tenant_id, company_id, created_at)` |
| company_id | UUID (FK companies) NOT NULL, index | |
| deal_id, contact_id | UUID (FK) nullable | |
| tipo | String(30) NOT NULL | enum: ligacao/email/reuniao/tarefa/cadastro/pipeline/nota |
| titulo | String(255) NOT NULL | |
| descricao | Text | |
| evento_meta (col. `metadata`) | JSONB | payload livre do evento |
| user_id | UUID (FK users) nullable | autor do evento |

#### `import_jobs`
| Campo | Tipo | Notas |
|---|---|---|
| id | UUID (PK) | |
| tenant_id | UUID (FK) | |
| tipo | String(20) NOT NULL | enum: empresas/contatos |
| arquivo | String(255) NOT NULL | hoje é apenas nome; **precisa apontar para storage real (G10)** |
| status | String(20) default `pendente` | enum: pendente/processando/concluido/erro |
| total_linhas, importadas | Integer | |
| erros | JSONB | lista de `{linha, motivo}` |
| created_by | UUID (FK users) | |

#### `audit_logs`
| Campo | Tipo | Notas |
|---|---|---|
| id | UUID (PK) | |
| tenant_id | UUID (FK) | |
| user_id | UUID (FK users) nullable | |
| entidade | String(40) NOT NULL | nome da entidade afetada |
| entidade_id | UUID nullable | |
| acao | String(20) NOT NULL | enum: create/update/delete/login |
| diff | JSONB | |
| ip | String(45) | |

### 2.2 Tabelas novas — Fase 2 (Sequências, Cadências, Workflows)

> Desenho proposto; nomes/campos a validar com o PO antes da implementação, conforme feedback já registrado do usuário sobre protótipos antes de mudanças de schema.

#### `sequences` (RF010 — Sequências de Tarefas)
| Campo | Tipo | Notas |
|---|---|---|
| id | UUID (PK) | |
| tenant_id | UUID (FK) | |
| nome | String(120) NOT NULL | |
| ativo | Boolean default true | |
| pausar_em_resposta | Boolean default true | regra "pausar quando houver resposta" |
| created_by | UUID (FK users) | |

#### `sequence_steps`
| Campo | Tipo | Notas |
|---|---|---|
| id | UUID (PK) | |
| sequence_id | UUID (FK sequences), index | |
| ordem | Integer NOT NULL | |
| dia_offset | Integer NOT NULL | dias a partir do início (0, 3, 7, 14…) |
| tipo | String(20) NOT NULL | ligacao/email/whatsapp/followup |
| template_id | UUID (FK email_templates) nullable | quando tipo = email |
| instrucoes | Text nullable | roteiro para ligação/whatsapp |

#### `sequence_enrollments`
| Campo | Tipo | Notas |
|---|---|---|
| id | UUID (PK) | |
| sequence_id | UUID (FK sequences), index | |
| company_id / contact_id / deal_id | UUID (FK) nullable | alvo da sequência |
| status | String(20) default `ativa` | ativa/pausada/concluida/cancelada |
| step_atual | Integer default 0 | |
| pausado_motivo | String(60) nullable | ex.: `resposta_recebida` |
| iniciado_em, atualizado_em | DateTime(tz) | |
| índice | `(tenant_id, status, step_atual)` | usado pelo Celery Beat para varrer pendências |

#### `cadences` + `cadence_steps` + `cadence_enrollments` (RF011 — Cadência de E-mails)

Estrutura análoga a `sequences`, mas restrita a e-mail, com `email_templates` (assunto, corpo, variáveis `{{nome}}`, `{{empresa}}`, `{{cargo}}`, `{{responsavel}}`) e `dias_espera` entre envios.

> **Recomendação de arquitetura:** `sequences` e `cadences` compartilham o mesmo padrão de máquina de estados (enrollment → step atual → pausar/retomar/clonar). Considerar modelar como **um único motor de sequenciamento genérico** (`sequence_type = tarefas | email`) em vez de duas implementações paralelas, para não duplicar o scheduler do Celery Beat e a lógica de pausa por resposta. Divergir do documento de requisitos aqui é só de implementação interna — a experiência de usuário (duas telas distintas) pode ser mantida.

#### `email_templates`
| Campo | Tipo | Notas |
|---|---|---|
| id | UUID (PK) | |
| tenant_id | UUID (FK) | |
| nome, assunto | String | |
| corpo | Text | suporta variáveis dinâmicas |
| variaveis_disponiveis | JSONB | lista de placeholders válidos |

#### `workflows` (RF018)
| Campo | Tipo | Notas |
|---|---|---|
| id | UUID (PK) | |
| tenant_id | UUID (FK) | |
| nome | String(120) | |
| gatilho | String(40) NOT NULL | empresa_criada/contato_criado/negocio_criado/mudanca_etapa/resposta_recebida |
| condicoes | JSONB nullable | filtros opcionais (ex.: só se `pipeline_id = X`) |
| ativo | Boolean default true | |

#### `workflow_actions`
| Campo | Tipo | Notas |
|---|---|---|
| id | UUID (PK) | |
| workflow_id | UUID (FK workflows), index | |
| ordem | Integer | |
| tipo_acao | String(40) NOT NULL | criar_tarefa/enviar_email/alterar_pipeline/notificar_usuario/executar_enriquecimento |
| parametros | JSONB | payload específico da ação |

#### `workflow_execution_logs`
| Campo | Tipo | Notas |
|---|---|---|
| id | UUID (PK) | |
| workflow_id | UUID (FK), index | |
| entidade_ref | UUID | registro que disparou o workflow |
| resultado | String(20) | sucesso/erro |
| detalhes | JSONB | |
| executado_em | DateTime(tz) | |

### 2.3 Tabelas novas — Fase 3 (IA e Enriquecimento)

#### `enrichment_batches` / extensão de `import_jobs`
Reaproveitar o padrão de `ImportJob` para lotes de enriquecimento, com etapas próprias (RF016): `importado → aguardando_enriquecimento → em_processamento → revisao → aprovado → rejeitado`.

| Campo | Tipo | Notas |
|---|---|---|
| id | UUID (PK) | |
| tenant_id | UUID (FK) | |
| status | String(30) NOT NULL | etapas acima |
| provider | String(20) | openai/claude |
| criado_por | UUID (FK users) | |

#### `company_enrichments` (1:1 ou 1:N com `companies`)
| Campo | Tipo | Notas |
|---|---|---|
| id | UUID (PK) | |
| company_id | UUID (FK companies), index | |
| batch_id | UUID (FK enrichment_batches) | |
| status | String(20) | aguardando/processando/revisao/aprovado/rejeitado |
| dados_sugeridos | JSONB | segmento, porte, produtos, serviços, nº funcionários, tecnologias, redes sociais, presença digital, perfil comercial |
| resumo_executivo | Text | saída da IA |
| revisado_por | UUID (FK users) nullable | |
| revisado_em | DateTime(tz) nullable | |

#### `ai_interactions` (log/auditoria de uso de IA — RF017)
| Campo | Tipo | Notas |
|---|---|---|
| id | UUID (PK) | |
| tenant_id | UUID (FK) | |
| user_id | UUID (FK users) | |
| tipo | String(30) | gerar_email/gerar_script/resumir_empresa/sugerir_proxima_acao/plano_abordagem |
| entidade_ref | UUID nullable | empresa/contato/negócio relacionado |
| provider, modelo | String | openai/claude + nome do modelo |
| prompt, resposta | Text | |
| tokens_entrada, tokens_saida | Integer nullable | custo/observabilidade |
| created_at | DateTime(tz) | |

### 2.4 Índices — resumo do que já existe e do que se recomenda adicionar

Já criados na migração inicial: `ix_companies_tenant_status`, `ix_deals_tenant_stage`, `ix_deals_tenant_resp`, `ix_tasks_tenant_resp_status`, `ix_timeline_tenant_company`.

Recomendados para as fases novas: `(tenant_id, status, step_atual)` em enrollments (varredura do Beat), `(tenant_id, gatilho)` em `workflows`, `(company_id, status)` em `company_enrichments`.

---

## 3. Estratégia Multi-Tenant

### 3.1 Isolamento por empresa — já implementado, em 3 camadas

1. **JWT como única fonte do `tenant_id`.** O token de acesso carrega `sub` (user), `tenant_id` e `perfil`. Nenhum endpoint aceita `tenant_id` vindo do corpo da requisição.
2. **Contexto de requisição (`ContextVar`).** `get_current_user` (dependency) decodifica o JWT e chama `set_current_tenant`/`set_current_user` **antes** de qualquer consulta — o tenant fica disponível para toda a stack via `app/core/context.py`.
3. **`BaseRepository` genérico.** Toda leitura (`get`, `list`) já parte de `select(model).where(model.tenant_id == tenant_atual)`; toda escrita (`add`) sobrescreve `obj.tenant_id` com o valor do contexto, ignorando qualquer valor externo.
4. **RLS no Postgres (defesa em profundidade).** Um listener SQLAlchemy (`after_begin`) executa `SET LOCAL app.current_tenant = <uuid>` a cada transação; as policies `USING (tenant_id = current_setting('app.current_tenant', true)::uuid)` bloqueiam qualquer query que, por bug, escape do filtro em código. `FORCE ROW LEVEL SECURITY` garante que isso vale mesmo para o dono da tabela.

Esse desenho já é adequado para SaaS multiempresa em schema compartilhado (RNF007) na escala esperada (RNF008 — 100k+ empresas por tenant): `SET LOCAL` é compatível com pooling de conexões em modo transação (ex.: PgBouncer), pois o valor vale só durante a transação corrente — importante manter essa restrição ao evoluir a infraestrutura.

**Gap:** não há hoje um fluxo de **provisionamento de novo tenant** (self-service signup). `app/seed.py` cria manualmente o primeiro tenant/admin. Para RNF007 (SaaS) será necessário um endpoint/rotina de onboarding (criação de tenant + admin inicial + e-mail de boas-vindas).

### 3.2 Controle de permissões

- **RBAC por perfil**, via dependency `require_roles(*perfis)` (`app/core/deps.py`), usado hoje em: gestão de usuários (admin), atualização de tenant (admin), CRUD de pipeline/stage (admin+gestor), dashboard comercial (admin+gestor).
- **Gap (G5):** os endpoints de Empresas, Contatos, Negócios e Tarefas usam apenas `get_current_user` (qualquer perfil ativo), sem checagem de perfil. Ou seja, hoje um `Visualizador` pode criar/editar/excluir — o que contradiz a intenção usual de um perfil "somente leitura". **Ação recomendada:** aplicar `require_roles` (ou uma variante `require_write`) nas rotas de mutação desses módulos, permitindo todos os perfis em `GET` mas restringindo `POST/PUT/PATCH/DELETE` a admin/gestor/vendedor.
- **Gap (G6 — a validar com o PO):** não há filtro de visibilidade por vendedor (um vendedor hoje enxerga todas as empresas/negócios do tenant, não só os seus). Se o requisito de negócio for "vendedor só vê a própria carteira, gestor vê tudo", isso precisa de um filtro adicional no `BaseRepository` ou nos services, condicionado ao perfil do usuário autenticado — hoje o repositório só conhece o tenant, não o usuário.

---

## 4. APIs REST

### 4.1 Já implementadas (fonte de verdade viva em `/docs`)

Para evitar duplicidade e desatualização, os payloads completos (todos os campos de `Create`/`Update`/`Read`) devem ser consultados no Swagger (`http://localhost:8000/docs`) — já gerado automaticamente pelo FastAPI a partir dos schemas Pydantic. Abaixo, o inventário de rotas por módulo:

| Módulo | Rotas |
|---|---|
| **Auth** (`/api/v1/auth`) | `POST /login`, `POST /refresh`, `POST /logout`, `POST /forgot-password`, `POST /reset-password`, `GET /me` |
| **Tenant** (`/api/v1/tenant`) | `GET ""`, `PUT ""` (admin) |
| **Usuários** (`/api/v1/users`) | `GET ""`, `POST ""`, `GET /{id}`, `PUT /{id}`, `PATCH /{id}/status` — todas admin-only |
| **Empresas** (`/api/v1/companies`) | `GET ""` (filtros: status, uf, busca), `POST ""`, `GET /{id}`, `PUT /{id}`, `PATCH /{id}/status`, `DELETE /{id}` (soft delete), `GET /{id}/timeline`, `POST /{id}/timeline` |
| **Contatos** (`/api/v1/contacts`) | `GET ""` (filtro company_id), `POST ""`, `GET /{id}`, `PUT /{id}`, `DELETE /{id}` |
| **Pipelines** (`/api/v1/pipelines`) | `GET ""`, `POST ""` (gestor+), `GET /{id}`, `PUT /{id}` (gestor+), `POST /{id}/stages` (gestor+), `PUT /{id}/stages/{stage_id}` (gestor+), `GET /{id}/board` (kanban) |
| **Negócios** (`/api/v1/deals`) | `GET ""` (filtros: pipeline_id, stage_id, status, responsavel_id), `POST ""`, `GET /{id}`, `PUT /{id}`, `PATCH /{id}/stage` (mover no board), `PATCH /{id}/close` |
| **Tarefas** (`/api/v1/tasks`) | `GET ""` (filtros: responsavel_id, status, tipo), `POST ""`, `GET /{id}`, `PUT /{id}`, `PATCH /{id}/complete`, `DELETE /{id}` |
| **Dashboards** (`/api/v1/dashboards`) | `GET /commercial` (admin+gestor), `GET /seller` (usuário logado) |

**Convenções já estabelecidas** (manter nas rotas novas):
- Listagens retornam envelope `Page[T]` (`items`, `total`, `page`, `size`).
- Erros retornam envelope `{ "error": { "code", "message", "details" } }` (ver `app/core/exceptions.py`).
- Todas as rotas exigem `Authorization: Bearer <access_token>`, exceto `login`, `refresh`, `forgot-password`, `reset-password`.

### 4.2 A completar no MVP (backend já tem a base, falta só a rota)

| Rota proposta | Método | Notas |
|---|---|---|
| `/api/v1/companies/import` | `POST` (multipart) | recebe arquivo, cria `ImportJob`, dispara `import_companies_task` |
| `/api/v1/contacts/import` | `POST` (multipart) | idem, dispara `import_contacts_task` |
| `/api/v1/import-jobs/{id}` | `GET` | consulta status/erros do job |
| `/api/v1/companies/export` | `GET` (`?format=xlsx|csv`) | RF021 |
| `/api/v1/contacts/export` | `GET` | RF021 |
| `/api/v1/deals/export` | `GET` | RF021 |
| `/api/v1/tasks/export` | `GET` | RF021 |
| `/api/v1/reports/commercial` | `GET` (`?format=xlsx|pdf`) | RF022 |
| `/api/v1/reports/activities` | `GET` (`?format=xlsx|pdf`) | RF023 |

### 4.3 Fase 2 — Sequências, Cadências, Workflows

| Módulo | Rotas propostas |
|---|---|
| Sequências | `GET/POST /sequences`, `GET/PUT /sequences/{id}`, `POST /sequences/{id}/steps`, `POST /sequences/{id}/enroll`, `POST /sequences/{id}/clone`, `PATCH /enrollments/{id}/pause`, `PATCH /enrollments/{id}/resume` |
| Cadências | `GET/POST /cadences`, `GET/PUT /cadences/{id}`, `POST /cadences/{id}/steps`, `POST /cadences/{id}/enroll` |
| Templates de e-mail | `GET/POST /email-templates`, `GET/PUT/DELETE /email-templates/{id}` |
| Workflows | `GET/POST /workflows`, `GET/PUT /workflows/{id}`, `POST /workflows/{id}/actions`, `GET /workflows/{id}/logs` |

### 4.4 Fase 3 — IA e Enriquecimento

| Módulo | Rotas propostas |
|---|---|
| Enriquecimento | `POST /companies/{id}/enrich`, `POST /enrichment/batches` (lote), `GET /enrichment/batches/{id}`, `PATCH /enrichment/items/{id}/approve`, `PATCH /enrichment/items/{id}/reject` |
| Assistente IA | `POST /ai/generate-email`, `POST /ai/generate-call-script`, `POST /ai/summarize-company/{id}`, `POST /ai/next-action/{deal_id}`, `POST /ai/approach-plan/{company_id}` |

---

## 5. Estrutura Frontend (a construir)

### 5.1 Árvore de pastas proposta

```
frontend/
  src/
    app/                # bootstrap, providers (QueryClient, ThemeProvider, Router)
    theme/               # tema MUI com paleta GD Conecta
    api/                 # client axios + funções por recurso (companies.ts, deals.ts, ...)
    hooks/               # hooks React Query por recurso (useCompanies, useDeals, ...)
    routes/              # definição de rotas + guarda de autenticação/perfil
    layout/              # AppShell (sidebar + topbar), AuthLayout
    features/
      auth/
      dashboard/
      companies/         # lista, detalhe (com timeline), formulário
      contacts/
      deals/             # board kanban + lista
      pipelines/          # configuração de pipeline/etapas (admin/gestor)
      tasks/
      users/              # admin
      settings/           # dados do tenant
      sequences/          # fase 2
      cadences/           # fase 2
      workflows/          # fase 2
      ai/                  # fase 3
    components/           # DataTable, KanbanBoard, TimelineFeed, StatusBadge, FormDialog, RoleGuard
```

### 5.2 Rotas

| Rota | Tela | Acesso |
|---|---|---|
| `/login`, `/esqueci-senha`, `/redefinir-senha` | Autenticação | público |
| `/` | Dashboard (comercial ou vendedor, conforme perfil) | autenticado |
| `/pesquisa-leads` | Pesquisa de Leads — pré-CRM, ICP score/fit, gamificação (§9.1) | autenticado |
| `/pesquisa-leads/desempenho` | Relatório de Desempenho de Pesquisa (§9.7) | admin/gestor |
| `/empresas` | Lista de empresas (filtros: status, UF, busca) | autenticado |
| `/empresas/:id` | Detalhe (dados cadastrais + timeline + negócios + contatos) | autenticado |
| `/contatos` | Lista de contatos | autenticado |
| `/negocios` | Board kanban (drag-and-drop) + alternância para lista | autenticado |
| `/negocios/:id` | Detalhe do negócio — protótipo aprovado (§9.4) | autenticado |
| `/pipelines` | Configuração de pipelines/etapas | admin/gestor |
| `/tarefas` | Lista/agenda de tarefas | autenticado |
| `/formularios` | Gestão de formulários de captura + rastreio de visitantes do site (§9.8) | admin/gestor |
| `/sequencias`, `/cadencias`, `/workflows` | Fase 2 — UI prototipada (§9.5) | admin/gestor |
| `/modelos-email`, `/snippets` | Conteúdo reutilizável — modelos de e-mail (Fase 2) e snippets (§9.6) | autenticado |
| `/usuarios` | Gestão de usuários | admin |
| `/configuracoes` | Dados do tenant + histórico de importações (§9.3) | admin |
| `/preferencias` | Preferências pessoais — perfil, e-mail/calendário (Microsoft 365), chamadas, segurança (§9.2) | autenticado |
| `/ia`, `/enriquecimento` | Fase 3 | admin/gestor |

> Import/Export **não tem rota própria** — os botões ficam embutidos em `/empresas`, `/contatos`, `/negocios` e `/tarefas`; o histórico cross-entidade fica em `/configuracoes` (§9.3).

### 5.3 Componentes reutilizáveis principais

- **DataTable paginada** (server-side, integrada ao envelope `Page[T]`).
- **KanbanBoard** (dnd-kit ou similar) para o board de pipeline, com `PATCH /deals/{id}/stage` no drop.
- **TimelineFeed** para o histórico de interações da empresa.
- **RoleGuard** (wrapper de rota) que esconde/bloqueia por `perfil`, refletindo o RBAC do backend — reforço de UX, nunca a única barreira de segurança.
- **FormDialog** genérico para criar/editar entidades em modal.
- **StatusBadge** para os enums de status (lead/qualificado/cliente…, aberto/ganho/perdido…).

### 5.4 Layout

Shell padrão: sidebar de navegação (itens condicionados ao perfil), topbar com busca global, notificações (quando workflows existirem) e avatar/logout. Tema MUI usando a paleta oficial da marca (ver §1.3) e tipografia IBM Plex Sans/Mono.

---

## 6. Estrutura Backend

### 6.1 Módulos (convenção já estabelecida, a repetir em módulos novos)

```
app/
  api/v1/<recurso>.py       # router HTTP — validação e autorização, sem regra de negócio
  schemas/<recurso>.py      # Create / Update / Read / filtros de listagem
  services/<recurso>.py     # regra de negócio, transação, timeline, auditoria
  repositories/<recurso>.py # acesso a dados, herda BaseRepository
  models/<recurso>.py       # ORM + mixins (Tenant, Timestamp, SoftDelete)
  workers/tasks.py          # tarefas Celery
  core/                     # config, database, security, context, deps, celery_app, exceptions
```

Ao criar um módulo novo (ex.: `sequences`), seguir exatamente essa ordem: model → repository → schema → service → router → registrar em `app/api/router.py`. Isso é o padrão já validado no MVP e evita inconsistência arquitetural.

### 6.2 Responsabilidades por camada (contrato já em vigor)

| Camada | Responsabilidade | Não deve conter |
|---|---|---|
| `api/` | Parsing de request, dependências de auth/autorização, chamar o service, mapear resposta | Regra de negócio, acesso a dados |
| `schemas/` | Validação de formato/tipo (Pydantic) | Regra de negócio |
| `services/` | Regras de negócio, orquestração entre repositórios, registro de timeline/auditoria, transações | Acesso direto ao ORM fora do repository |
| `repositories/` | Query building, filtro de tenant automático (via `BaseRepository`) | Regra de negócio |
| `models/` | Mapeamento de tabela, mixins, enums de domínio | Lógica de aplicação |

### 6.3 Workers (Celery) — já existentes e a adicionar

**Já existe:** `import_companies_task`, `import_contacts_task` (fila `default`), com propagação manual de tenant/usuário para o contexto (mesmo padrão de isolamento do request HTTP).

**A adicionar:**
- `celery beat` (novo serviço no compose) com schedule para: varrer `sequence_enrollments`/`cadence_enrollments` com step vencido e disparar a ação (criar tarefa, enviar e-mail); varrer SLA de etapas de pipeline (`pipeline_stages.sla_horas`) para alertas.
- Tarefa de envio de e-mail (SMTP/provedor) reaproveitável por: reset de senha, cadências, notificações de workflow.
- Tarefa de chamada aos provedores de IA (enriquecimento e assistente), com fila dedicada (para não competir com import) e retry/backoff (chamadas externas).
- Tarefa de execução de `workflow_actions` (fila dedicada, disparada de forma assíncrona a partir dos gatilhos).

---

## 7. Fluxos de Negócio

### 7.1 Empresas (RF004–RF005) — implementado

`Lead → Qualificado → Cliente` (ou `Perdido`/`Inativo`), com histórico completo em `timeline_events`. Toda mutação relevante (cadastro, mudança de status, negócios associados) já é registrada na timeline pelo `TimelineService`. Import em massa (Excel/CSV) já processa de forma assíncrona (Celery), validando campos obrigatórios (`razao_social`, `cnpj`, `cidade`, `uf`) e duplicidade de CNPJ por tenant — falta apenas a rota HTTP de disparo (§4.2).

### 7.2 Contatos (RF006) — implementado

Múltiplos contatos por empresa via `company_id`. Sem regra de negócio adicional além do CRUD.

### 7.3 Negócios e Pipeline (RF007–RF008) — implementado

Negócio pertence a uma `company`, opcionalmente a um `contact`, sempre a um `responsavel` (vendedor), e vive em um `pipeline`/`stage`. Mover de etapa (`PATCH /deals/{id}/stage`) e fechar (`PATCH /deals/{id}/close`, com `motivo_perda` quando perdido) já são endpoints dedicados — coerente com o board kanban de arrastar-e-soltar do requisito. SLA por etapa (`sla_horas`) já existe no modelo; falta o disparo automático de alerta (depende do Celery Beat, §6.3).

### 7.4 Tarefas (RF009) — implementado

CRUD completo + `complete`. Vínculo opcional a empresa/contato/negócio.

### 7.5 Sequências de Tarefas (RF010) — a construir

Fluxo: enroll de uma empresa/contato/negócio em uma `sequence` → Celery Beat varre `sequence_enrollments` diariamente → para cada step vencido (`dia_offset`), cria uma `Task` (ligação/e-mail/whatsapp/follow-up) atribuída ao responsável → avança `step_atual`. Regra "pausar quando houver resposta" **depende de um sinal de resposta recebida**, que só existe se houver integração de caixa de entrada (**Microsoft 365/Graph** — a GD Conecta usa essa suíte corporativamente, ver §9.2 — não Gmail/Outlook genérico) — ou seja, a integração de e-mail é pré-requisito técnico dessa regra, não pode ser implementada isoladamente. Clonar sequência e reiniciar são operações de service simples sobre `sequences`/`sequence_steps`.

### 7.6 Cadência de E-mails (RF011) — a construir

Mesmo motor de enrollment de §7.5, restrito a `tipo = email`, com `email_templates` e variáveis dinâmicas resolvidas no momento do envio (substituição de `{{nome}}`, `{{empresa}}`, `{{cargo}}`, `{{responsavel}}`). Ao final do fluxo (ex.: e-mail 3), criação automática de tarefa de follow-up — reaproveita o mesmo mecanismo de criação de `Task` de §7.5.

### 7.7 IA (RF015–RF017) — a construir

Três casos de uso distintos, todos passando por uma camada de abstração de provedor (`app/services/ai/`) com adaptadores OpenAI/Claude:
1. **Enriquecimento de empresa** (§7.8) — entrada estruturada (CNPJ, razão social, site) → saída estruturada + resumo executivo.
2. **Assistente comercial** — geração de e-mail/script/resumo/próxima ação/plano de abordagem, a partir do contexto de uma empresa/negócio já cadastrado. Cada chamada é logada em `ai_interactions` (auditoria de custo e conteúdo gerado).
3. Ambos os casos devem ser **assíncronos quando envolvem lote** (enriquecimento em massa) e **síncronos** quando é uma ação pontual do usuário (gerar um e-mail agora), mas sempre com timeout e fallback de erro tratado (chamada a provedor externo pode falhar).

### 7.8 Enriquecimento (RF016) — a construir

Máquina de estados por empresa: `importado → aguardando_enriquecimento → em_processamento → revisao → aprovado/rejeitado`. Processamento em lote via Celery; aprovação é sempre manual (humano no loop) antes de os dados sugeridos sobrescreverem o cadastro da empresa — reaproveita o padrão de revisão já usado no `import_jobs` (aprovar erros linha a linha).

### 7.9 Workflows (RF018) — a construir

Motor evento→condição→ação: os gatilhos (`empresa_criada`, `contato_criado`, `negocio_criado`, `mudanca_etapa`, `resposta_recebida`) devem ser publicados pelos services existentes (ex.: `CompanyService.create` publica `empresa_criada`) para um dispatcher que localiza `workflows` ativos com aquele gatilho e enfileira as `workflow_actions` correspondentes via Celery. Ação `executar_enriquecimento` conecta workflows diretamente ao módulo de IA (§7.8).

---

## 8. Roadmap Técnico

| Fase | Escopo | Status | Principais dependências |
|---|---|---|---|
| **Fase 0** | Backend MVP (Auth, Multiempresa, Usuários, Empresas+Timeline, Contatos, Negócios, Pipeline, Tarefas, Dashboards Comercial/Vendedor) | ✅ Concluída | — |
| **Fase 0.5 — Pesquisa de Leads** | Novo domínio pré-CRM (§9.1): entidade `lead_prospects`, Score ICP/ICP Fit configurável por tenant, gamificação/bônus, promoção para `companies`. Frontend prototipado e aprovado; backend 0% | 🔲 A fazer | Nenhuma externa |
| **Fase 1 — Fechamento do MVP** | Endpoints de import/export (§4.2, embutidos nas telas por entidade — §9.3), envio de e-mail (reset de senha), hardening de RBAC (G5/G6), frontend completo (§5), testes automatizados + CI mínimo, observabilidade básica, rotação de `SECRET_KEY`, storage de arquivos, Preferências pessoais + integração Microsoft 365/Graph (§9.2), Snippets (§9.6) | 🔲 A fazer | Nenhuma externa — é só volume de trabalho sobre o que já existe |
| **Fase 2** | Sequências de Tarefas, Cadência de E-mails, Workflows, Modelos de e-mail, integração **Microsoft 365/Graph** (necessária para "pausar por resposta") e WhatsApp. Frontend prototipado e aprovado (§9.5); backend 0% | 🔲 A fazer | Conta Microsoft 365 conectada (já decidido usar Graph API); API do WhatsApp Business |
| **Fase 3** | IA Comercial (assistente), Enriquecimento Inteligente, Score de Leads, recomendações automáticas | 🔲 A fazer | Chaves OpenAI/Claude; orçamento de custo por chamada de IA |
| ~~SaaS self-service~~ | **Deprioritizado** — o CRM é de uso interno da GD Conecta, não será comercializado a princípio (§9.0). A arquitetura multi-tenant/RLS continua válida e não muda; só o onboarding self-service de novos tenants perde prioridade. | ⏸️ Fora de escopo por ora | — |
| **Fase 4** | Marketplace de integrações, BI avançado, forecast com IA, motor de prospecção inteligente | 🔲 A fazer | Fases 2–3 concluídas e validadas com uso real |

### Observação final sobre viabilidade

Não há nenhum item, nas fases 1–4, que exija reescrever a base já construída. O risco maior não é técnico — é de **sequenciamento**: iniciar Fase 2/3 antes de fechar os gaps de Fase 1 (especialmente testes automatizados e frontend) tende a multiplicar retrabalho, porque cada fase nova depende de telas e de confiança de regressão que ainda não existem.

---

## 9. Módulos e Decisões Adicionados Após a Especificação Inicial (2026-07-27)

Uma rodada de prototipagem de frontend (13 protótipos interativos, todos aprovados pelo usuário) revelou requisitos e decisões de produto que **não estavam** no documento funcional original nem nas seções 1–8 acima. Esta seção é a fonte de verdade para esses itens; onde ela contradiz uma seção anterior (ex.: Gmail/Outlook → Microsoft 365), **esta seção prevalece**.

### 9.0 Decisão fundamental: uso interno, não SaaS comercializável

O GD CRM é para **uso interno da própria GD Conecta** — não será comercializado/revendido a princípio. Isso não muda a arquitetura (multi-tenant + RLS continuam corretos e não devem ser removidos, é o padrão certo independentemente de revenda), mas muda a priorização:

- O item "SaaS multiempresa self-service" da Fase 3 (onboarding automático de novos tenants) fica **fora de escopo por ora** — GD Conecta é, na prática, o único tenant relevante no curto/médio prazo.
- Não implementar cobrança/revenda de minutos de chamada, planos pagos para outros tenants, ou onboarding self-service **sem pedido explícito** do usuário.
- `tenants.config` (JSONB) segue sendo o mecanismo correto para configurações por tenant (ex.: pesos de ICP score — §9.1), já que "GD Conecta ser o único tenant hoje" não significa que o próximo tenant (se algum dia existir) devesse herdar regras hardcoded.

### 9.1 Pesquisa de Leads (novo domínio, pré-CRM)

Processo que hoje roda numa planilha Notion — um funcionário pesquisa/enriquece empresas (com apoio do Claude Chat) antes de elas virarem oficialmente `companies`. Motivo de existir fora de `companies`: nem toda pesquisa vira lead (descartes e "não avaliados" não devem poluir o cadastro oficial); só quando o registro atinge status `promovido` é que ele gera uma linha em `companies`.

#### Tabela `lead_prospects`

| Campo | Tipo | Notas |
|---|---|---|
| id | UUID (PK) | |
| tenant_id | UUID (FK) | |
| empresa | String(255) NOT NULL | nome da empresa pesquisada (ainda não é `companies.razao_social` oficial) |
| setor | String(80) nullable | categoria macro — **define pontos do Score ICP** |
| segmento | String(120) nullable | subcategoria informativa dentro do setor, não pontua |
| uf | String(2) nullable | região (Sudeste/Sul/Nordeste/Norte/Centro-Oeste) é **derivada** de `uf`, não armazenada |
| faixa_funcionarios | String(20) nullable | enum de faixas (`1-50` … `+ de 10.001`) — dado primário, já que fontes como LinkedIn só dão faixa, não número exato |
| faturamento | Numeric(15,2) nullable | |
| site, telefone, linkedin | String | |
| dor_sugerida | Text nullable | hipótese de dor levantada na pesquisa; hoje preenchida manualmente via Claude Chat — na Fase 3 pode ser automatizada por `company_enrichments` |
| contato_sugerido | String(255) nullable | texto livre (nome/cargo) — vira `contacts` de verdade só após a promoção |
| status | String(20) NOT NULL default `pesquisando` | enum: pesquisando/enriquecido/pronto_para_cadencia/promovido/descartado |
| pesquisado_por | UUID (FK users) NOT NULL | essencial para o relatório de desempenho (§9.7) |
| promoted_company_id | UUID (FK companies) nullable | preenchido quando promovido — mantém rastreabilidade/auditoria |
| created_at | DateTime(tz) | substitui a coluna "Mês" da planilha — agrupar por mês a partir daqui |

**Campos calculados em service (não persistidos como colunas — recalculados a cada leitura, custo desprezível mesmo em escala):**

- `score_icp` = `min(100, pontos_setor + pontos_regiao + pontos_faixa)`, onde os três pesos vêm de `tenants.config.icp_scoring_rules` (ver abaixo) — **nunca hardcoded no código**, porque isso trava o produto num critério só da GD Conecta.
- `icp_fit`: `"Não avaliado"` se score=0 e setor/uf/faixa todos vazios; senão `A` (≥ corte_a), `B` (≥ corte_b), `C` (≥ corte_c), `Sem Perfil` (abaixo).
- `gamificacao` = 0 se `icp_fit` ∈ {C, Sem Perfil, Não avaliado} ou status=descartado; senão soma pontos fixos por campo preenchido (telefone 40, setor 20, uf 20, faixa 10, site 10 — total 100).
- `recebe_bonus` = `status == "promovido" AND gamificacao > 70`. **Importante:** gamificação alta sozinha não paga bônus — só conta quando a pesquisa virou empresa de verdade. Antes disso o bônus é "pendente", não "válido".
- `bonus_valor` = `recebe_bonus ? tenants.config.icp_scoring_rules.bonus_valor : 0`.

#### `tenants.config.icp_scoring_rules` (JSONB, por tenant)

```json
{
  "setor": { "Farma": 40, "Alimentos": 40, "Autopeças": 40, "Etiquetas": 40,
             "Plástico": 30, "Máquinas e Equipamentos": 30, "Química": 30, "Cosmético": 30 },
  "setor_fallback": 10,
  "regiao": { "Sudeste": 30, "Sul": 30, "Nordeste": 30, "Norte": 0, "Centro-Oeste": 0 },
  "faixa_funcionarios": { "1-50": 0, "51-200": 30, "201-500": 30, "501-1.000": 30,
                          "1.001-5.000": 40, "5.001-10.000": 50, "+ de 10.001": 0 },
  "corte_a": 80, "corte_b": 70, "corte_c": 40,
  "bonus_valor": 1.00
}
```

Setores fora do mapa pontuam `setor_fallback`. Região nunca é um campo de UI/armazenamento — é sempre `uf → regiao` via mapeamento fixo de estados brasileiros.

#### Fluxo de promoção

Ação `POST /lead-prospects/{id}/promote`: cria um registro em `companies` (status inicial `lead`, campos copiados de `lead_prospects`), grava `promoted_company_id` de volta no `lead_prospects` (nunca apaga o registro de pesquisa — ele vira histórico permanente, necessário para a apuração de bônus), e muda `status` para `promovido`.

#### Rotas propostas

| Rota | Método | Notas |
|---|---|---|
| `/api/v1/lead-prospects` | `GET` (filtros: status, icp_fit, pesquisado_por), `POST` | |
| `/api/v1/lead-prospects/{id}` | `GET`, `PUT`, `DELETE` | |
| `/api/v1/lead-prospects/{id}/promote` | `POST` | cria `companies`, atualiza status |
| `/api/v1/tenant/icp-scoring-rules` | `GET`, `PUT` (admin) | edita `tenants.config.icp_scoring_rules` |
| `/api/v1/lead-prospects/performance-report` | `GET` (`?mes=2026-07`) | agregação por `pesquisado_por` — alimenta §9.7 |

#### HubSpot

O fluxo antigo ("ao enriquecer, integra com o HubSpot") **não existe mais** — confirmado pelo usuário em 2026-07-27 ("não teremos a HubSpot mais"). O CRM GD Conecta (Negócios/Pipeline, e futuramente Cadências) é o único destino depois de "pronto para cadência". Não adicionar campos `hubspot_url`/`hubspot_company_id`.

### 9.2 Preferências pessoais e integrações (Microsoft 365)

Diferente de `/configuracoes` (dados do tenant, admin-only), **Preferências** é por usuário — qualquer perfil configura a própria conta. A GD Conecta usa **Microsoft 365/Outlook** corporativamente — por isso a integração de e-mail/calendário é **Microsoft Graph API** (OAuth por usuário), não IMAP/SMTP genérico nem Gmail.

#### Tabela `user_integrations` (nova)

| Campo | Tipo | Notas |
|---|---|---|
| id | UUID (PK) | |
| tenant_id, user_id | UUID (FK) | |
| provider | String(20) NOT NULL default `microsoft365` | |
| tipo | String(20) NOT NULL | enum: email/calendario |
| access_token_enc, refresh_token_enc | Text | **sempre criptografados em repouso** — nunca token em texto plano no banco |
| conectado_em | DateTime(tz) | |
| ativo | Boolean default true | |

#### Chamadas — decisão de escopo

Como é uso interno de equipe pequena, a solução recomendada **não é** um discador embutido (WebRTC/Twilio) desde já — é o caminho barato: links `tel:`/`wa.me` (já usados nas telas de Contatos/Empresas/Negócio-detalhe) + registro manual via `Task`/`timeline_events` (`tipo=ligacao`, já suportado no schema atual, nenhuma tabela nova necessária). Um discador de verdade (Twilio Voice, por melhor suporte a numeração brasileira) só vale a pena se o volume de ligações justificar — nesse caso, "minutos" seria só um painel de consumo/custo interno da GD Conecta, nunca uma cobrança a terceiros (não há terceiros).

#### Rotas propostas

| Rota | Método | Notas |
|---|---|---|
| `/api/v1/me/integrations/email` | `GET`, `POST` (inicia OAuth), `DELETE` (desconecta) | |
| `/api/v1/me/integrations/calendar` | `GET`, `POST`, `DELETE` | |
| `/api/v1/me/password` | `PUT` | trocar a própria senha |
| `/api/v1/me/sessions` | `GET`, `DELETE /{id}` | sessões ativas |

### 9.3 Importar/Exportar — sem tela dedicada

O documento original previa `/importar-exportar` como rota própria (§5.2 antiga). **Decisão do usuário:** melhor UX é embutir Importar/Exportar direto em cada tela de entidade (Empresas, Contatos, Negócios, Tarefas) — export respeita os filtros aplicados no momento; import abre um fluxo de upload com validação linha a linha (reaproveitando as mesmas regras de `import_companies_task`/`import_contacts_task`). O único ponto centralizado é o **histórico de jobs** (`import_jobs`, que já é uma tabela única com campo `tipo` — cross-entidade por natureza), exibido dentro de `/configuracoes`.

As rotas propostas em §4.2 continuam válidas tecnicamente (o backend não muda) — só a camada de apresentação deixa de ter uma tela própria.

### 9.4 Negócio (detalhe) — protótipo aprovado

`/negocios/:id` usa só rotas já existentes: `GET /deals/{id}`, `PATCH /deals/{id}/stage`, `PATCH /deals/{id}/close` (com `motivo_perda`), e a timeline da empresa filtrada por `deal_id`. Tela inclui: linha do tempo cronológica, compositor de atividade (nota/ligação/e-mail/reunião — grava em `timeline_events`), painel de detalhes editável (etapa/valor/probabilidade/previsão/origem), cards de empresa e contato principal vinculados, e tarefas vinculadas com conclusão inline.

### 9.5 Automação (Fase 2) — UI prototipada, backend pendente

Sequências, Cadências e Workflows (schema e rotas já propostos em §2.2/§4.3) tiveram a UI prototipada e aprovada. Confirmações do protótipo que valem registrar:

- **Clonar sequência/cadência** gera cópia **inativa e sem inscritos** — nunca copia `enrollments`.
- Cadência sempre tem um botão "Criar tarefa de follow-up ao final" (boolean + título) — reaproveita `Task`, não é uma tabela nova.
- Workflows: o diagrama gatilho→condição→ação da tela usa exatamente os 5 gatilhos já definidos em `workflows.gatilho`. A ação `executar_enriquecimento` aparece **desabilitada** na UI com nota explícita de dependência da Fase 3 — não bloquear o salvamento do workflow, só a execução dessa ação específica até a IA existir.
- Modelos de e-mail (`email_templates`): editor com inserção de variável por botão (não só digitação livre) e **guarda de exclusão** — um modelo referenciado por alguma `sequence_step`/`cadence_step` não pode ser excluído; a UI deve listar onde está em uso.

### 9.6 Snippets (novo domínio)

Conceito confirmado com o usuário (estilo "Snippets" do HubSpot): blocos de texto curtos reutilizáveis via atalho, **independentes** de Sequências/Cadências/Modelos de e-mail — servem para inserção rápida em notas, tarefas ou qualquer campo de texto do CRM, não só e-mail.

#### Tabela `snippets`

| Campo | Tipo | Notas |
|---|---|---|
| id | UUID (PK) | |
| tenant_id | UUID (FK) | |
| nome | String(120) NOT NULL | |
| atalho | String(40) NOT NULL | único **por tenant**; só `[a-z0-9]`, sem `#` armazenado (prefixo é só de exibição/digitação) |
| conteudo | Text NOT NULL | suporta as mesmas variáveis dinâmicas de `email_templates` (`{{nome}}`, `{{empresa}}`, `{{cargo}}`, `{{responsavel}}`) |
| created_by | UUID (FK users) | |

Expansão (`#atalho` + espaço → texto) é comportamento **client-side** (frontend detecta o padrão em qualquer `<textarea>`/campo de texto habilitado) — não precisa de endpoint dedicado além do CRUD padrão (`GET/POST /snippets`, `GET/PUT/DELETE /snippets/{id}`).

### 9.7 Relatório de Desempenho de Pesquisa

Não é uma entidade nova — é uma agregação sobre `lead_prospects`, agrupada por `pesquisado_por` e por mês (`created_at`). Tela somente-consulta (sem CRUD): ranking por taxa de qualificação (`icp_fit` A+B / total), volume de pesquisas por pessoa, e bônus válido total do mês (soma de `bonus_valor` onde `recebe_bonus = true`). **Não é um módulo de folha de pagamento** — só cálculo e consulta, com exportação CSV.

### 9.8 Formulários & Rastreio do site — correção de registro

Este módulo **já estava prototipado** (artifact único com duas abas) antes desta rodada de revisão — não é um gap. A aba Formulários cobre: KPIs de conversão, lista de formulários (status ativo/pausado/rascunho, código de incorporação, editar), últimos envios (marcando lead novo vs. empresa já existente), e um builder de campos por arrastar-e-soltar. A aba Rastreio do site cobre identificação de empresas visitantes por IP corporativo, tráfego por dia e páginas mais visitadas.

Esse módulo **não tem modelo de dados formalizado** nesta especificação ainda — ao implementar de verdade, será necessário desenhar `forms`, `form_fields` e `form_submissions` (hoje só existem como protótipo de frontend, sem schema correspondente em `2.1`/`2.2`).

### 9.9 Descartado: "Grupo de Usuários"

O usuário cogitou pedir uma tela de "Grupo de Usuários", mas ao esclarecer o que ela representaria (times/território? permissões customizadas além dos 4 perfis?) decidiu que **não precisa ser desenvolvida**. Não propor essa tela novamente sem pedido explícito.

### 9.10 Roadmap (não iniciado): lógica condicional de propriedades por etapa

Referência: [HubSpot — Customize properties shown in each stage](https://knowledge.hubspot.com/pt/object-settings/set-up-and-customize-pipelines#:~:text=Customize%20properties%20shown%20in%20each%20stage), trazida pelo usuário em 2026-07-28 junto com o pedido de cor de exibição do pipeline (§ acima, já implementado como `pipelines.cor_exibicao`).

**Ideia:** por etapa do pipeline, mostrar/exigir propriedades diferentes do negócio (ex.: "Motivo da perda" só aparece/obrigatório quando a etapa é `Fechado - Perdido"; "Valor do contrato assinado" só na etapa `Negociação` em diante).

**Por que não é um ajuste simples:** hoje `Deal` tem colunas fixas (nome, empresa, contato, responsável, valor_previsto, probabilidade, data_prev_fechamento, origem) — não existe conceito de **propriedade customizada** no schema. Pra ter lógica condicional de verdade (como o HubSpot faz) seria necessário construir antes um subsistema novo:
- tabela de definição de propriedades customizadas (nome, tipo, objeto associado — hoje só Negócio faria sentido);
- onde persistir o valor por negócio (provavelmente um `JSONB` em `deals` ou uma tabela EAV separada);
- um motor de regra (`propriedade-gatilho` + `operador` + `valor` → `mostrar`/`exigir` `propriedade-alvo`), similar ao "Editar lógica da propriedade" do HubSpot;
- UI de configuração na tela de Pipeline (por isso a coluna **"Regras de lógica condicional"** já está reservada — hoje com placeholder desabilitado "+ Adicionar lógica" — na tabela de etapas) e UI de aplicação em tempo real no formulário de Negócio (Novo/Editar).

**Decisão (2026-07-28):** não construir agora — é um projeto à parte, desproporcional ao restante do MVP. Retomar quando ficar claro, pelo uso real, quais propriedades de fato precisam variar por etapa — evita desenhar o motor de regras "no escuro", copiando a arquitetura do HubSpot sem necessidade comprovada.

### 9.11 Índice de protótipos produzidos

Todos os protótipos abaixo são artifacts interativos (HTML/CSS/JS autocontidos, dados mockados), aprovados pelo usuário, usados como referência de UX/fluxo para a implementação real em React — **não são código de produção** e os links são privados/efêmeros (considerar capturar screenshots ou re-exportar antes de trocar de conta ou depender deles a longo prazo).

| Tela | Rota proposta |
|---|---|
| Login | `/login` |
| Dashboard | `/` |
| Pesquisa de Leads | `/pesquisa-leads` |
| Desempenho de Pesquisa | `/pesquisa-leads/desempenho` |
| Empresas (lista + kanban) | `/empresas` |
| Empresa (detalhe) | `/empresas/:id` |
| Contatos | `/contatos` |
| Negócios (board) | `/negocios` |
| Negócio (detalhe) | `/negocios/:id` |
| Pipeline (configuração) | `/pipelines` |
| Tarefas | `/tarefas` |
| Sequências | `/sequencias` |
| Cadências | `/cadencias` |
| Workflows | `/workflows` |
| Modelos de e-mail | `/modelos-email` |
| Snippets | `/snippets` |
| Formulários & Rastreio do site | `/formularios` |
| Usuários | `/usuarios` |
| Configurações | `/configuracoes` |
| Preferências pessoais | `/preferencias` |

Detalhes de cada decisão de produto, links dos artifacts e o histórico completo da conversa que originou esta seção estão registrados na memória do projeto (fora deste repositório).
