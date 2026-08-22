# Plano — SDR Argos (agente comercial em dois níveis)

Status: **avaliação / proposta** — ainda não implementado. Evoluído a partir da análise de
"SDR autônomo end-to-end"; esta versão adota a arquitetura de **dois níveis** decidida em
discussão (aprendiz na Pesquisa de Leads → prospector na Empresas).

Protótipos de referência:
[`prototypes/sdr_na_pesquisa_leads_prototype.html`](prototypes/sdr_na_pesquisa_leads_prototype.html)
(gatilho embutido) e [`prototypes/sdr_autonomo_prototype.html`](prototypes/sdr_autonomo_prototype.html)
(fluxo de decisão) — ambos ilustram partes; o desenho canônico é o descrito abaixo.

> **Em uma frase.** Dois agentes, um por estágio do funil: um **aprendiz barato** enriquece e
> tria o lead cru na Pesquisa de Leads; depois da promoção, o **SDR Argos** (prospector capaz)
> monta o dossiê profundo, o argumento cruzado com o Benchmark Logístico, sugere a cadência e
> prepara a ligação — direto na tela de Empresas, reusando o que o Argos já tem.

---

## 0. Decisões travadas

1. **Dois níveis, dois agentes, um por estágio do funil.** Mapeia na fronteira de entidades que
   já existe (`LeadProspect` pré-CRM × `Company` pós-CRM) e no padrão de custo multiagente
   (worker barato para volume, agente capaz para julgamento).
2. **Pesquisa de Leads tem só um botão de IA: "Enriquecer com IA" (o aprendiz).** Preenche dados
   básicos e iniciais (setor, porte, UF, site, dor-hipótese). Modelo barato, alto volume, sob
   demanda. O antigo botão "Inteligência Comercial" **sai** desta tela.
3. **"SDR Argos" é o prospector, na tela de Empresas, estritamente pós-promoção (opção A).**
   Nenhum argumento comercial / inteligência é gerado antes da promoção. Consequência aceita: a
   decisão de **promover ou descartar** é tomada com **enriquecimento + Fit ICP apenas** — o
   argumento é sobre *como vender*, problema pós-promoção. (Perde-se a munição pré-promoção; foi
   uma escolha deliberada por simplicidade e custo.)
4. **A promoção Lead→Company é o handoff entre os dois agentes.** Ao promover, o SDR Argos
   acorda automaticamente na empresa (trabalho de leitura/rascunho, sem contato externo) — mesmo
   padrão do `CompanyAiService.regenerate_resumo`, que já roda automático a cada evento.
5. **O SDR Argos grava direto no `Company` — não há "fila de propostas" separada.** Ele é uma
   **expansão do `CompanyAiService`**, que já escreve `resumo_executivo`/`proxima_acao_sugerida`
   na empresa. Isso também **elimina a cópia** de `inteligencia_comercial` do lead para a
   empresa na promoção ([`lead_prospect.py:81`](../app/models/lead_prospect.py)): o prospector
   gera a IC direto no `Company`.
6. **O SDR Argos sugere a cadência, não inscreve.** A inscrição na sequência é um passo separado,
   **confirmado pelo humano** (pré-preenchido com a sugestão). Nenhum e-mail sai até essa
   confirmação — camada extra sobre a decisão nº 7.
7. **Nada de contato externo sem confirmação humana; anti-alucinação vira segurança.** Nome/
   e-mail de contato só entram se confirmados por fonte pública ou por provedor de dados com
   status `verificado` (§6). Nunca inventa. Num agente que dispara e-mail, isso é requisito de
   segurança, não cosmético.
8. **O SDR Argos prepara a ligação, não fala.** Gera roteiro + tarefa e usa o loop
   Twilio/AssemblyAI que já existe; voz autônoma fica fora de escopo (§8).
9. **Multi-tenant, RLS e auditoria valem para os dois agentes.** Ambos herdam `tenant_id`/
   `user_id` via o `ContextVar` de [`app/core/context.py`](../app/core/context.py); cada ação
   grava `TimelineEvent`.

---

## 1. Onde isto se encaixa no que já existe

**A maior parte das peças já existe** — o que falta é o encadeamento e o julgamento.

| Papel | Nível | Já existe? | Serviço |
|---|---|---|---|
| Enriquecer dados básicos (web) | Aprendiz | ✅ | `LeadEnrichmentService` |
| Calcular Fit ICP | Aprendiz | ✅ | `icp_scoring.calcular_icp` (determinístico) |
| Dossiê profundo + resumo + próxima ação | SDR Argos | ✅ (base) | `CompanyAiService.regenerate_resumo` |
| Cruzar com Benchmark Logístico | SDR Argos | ✅ | `CommercialIntelligenceService._resolver_benchmark` |
| Montar argumento comercial | SDR Argos | ✅ | `CommercialIntelligenceService.gerar` |
| Inscrever em cadência / disparar e-mail | (pós-decisão) | ✅ | `SequenceService.enroll` + `sequence_dispatch` |
| Ligação: gravar + transcrever + resumir | SDR Argos | ✅ | `twilio_voice` + `transcribe_call_recording_task` + `CompanyAiService` |
| Registrar na timeline | ambos | ✅ | `TimelineService` |
| **Contato verificado (e-mail de decisor)** | SDR Argos | ❌ | provedor B2B (§6) |
| **Decidir a sequência de passos e adaptar** | SDR Argos | ❌ | *é o que o agente adiciona* |

---

## 2. Especificação funcional — dois fluxos

### 2.1 Nível 1 — Aprendiz (Pesquisa de Leads)

1. O vendedor tem um lead cru (individual ou lote importado de feira/lista).
2. Clica **"Enriquecer com IA"** (individual ou em lote). O aprendiz preenche os campos básicos
   e calcula o Fit ICP.
3. O vendedor triaga olhando **Fit + dossiê básico**: promove os bons, descarta os fora de
   perfil. O descarte de perfil obviamente errado (ex.: transportadora, não embarcador) é
   evidente pelo Fit determinístico.
4. **Promover** faz o handoff → dispara o Nível 2.

O aprendiz **não** monta argumento nem cadência — só dá o suficiente para a decisão de perseguir.

### 2.2 Nível 2 — SDR Argos (Empresas, pós-promoção)

1. Na promoção, o SDR Argos roda **automaticamente** sobre a `Company` recém-criada (sem contato
   externo — é leitura/rascunho). Também há um botão **"SDR Argos"** na tela da empresa para
   re-rodar manualmente (mesmo padrão do botão "Atualizar agora" do resumo).
2. O prospector produz, gravando na própria empresa:
   - **Dossiê profundo** — decisor + **e-mail verificado** (via provedor B2B, §6), ERP/TMS, porte.
   - **Argumento comercial** cruzado com o Benchmark Logístico.
   - **Cadência sugerida** — qual sequência, para qual contato (sugestão, **sem inscrever**).
   - **Roteiro de ligação** personalizado (§8).
   - **Resumo executivo + próxima ação** — o que o `CompanyAiService` já faz, agora mais rico.
3. O vendedor revê na tela da empresa e, quando quiser abrir a cadência, **confirma a inscrição**
   (sequência pré-selecionada pela sugestão, editável). Só aí o 1º e-mail sai.

### 2.3 Fora de escopo (1ª fase)

- Voz autônoma (o SDR não fala com o cliente — §8).
- Disparo de cadência sem confirmação humana (meta de fase posterior, por flag e guardrails, §7).
- Decisão de preço/cotação (é do produto de frete, não do SDR).
- Inventar contato não encontrado (decisão travada nº 7).

---

## 3. Arquitetura

### 3.1 Onde roda o loop de cada agente

Recomendação inalterada em relação à análise original:

| Fase | Recomendação | Por quê |
|---|---|---|
| **Piloto** | **Managed Agents**, read-only | Prova o julgamento do prospector sem tocar no CRM; rápido e descartável. |
| **Produção** | **Tool Runner** na infra atual (`client.beta.messages.tool_runner` no Celery) | A stack já é madura (Celery + RLS + serviços prontos). Rodar o loop em casa é mais barato, mais seguro e sem plataforma nova. O maior valor do Managed Agents (sandbox hospedado) resolve um problema que vocês já têm resolvido. |

### 3.2 Modelo por nível

| Nível | Modelo sugerido | Racional |
|---|---|---|
| Aprendiz | **Haiku 4.5** (barato) | Alto volume, tarefa de preenchimento + Fit determinístico. Nota: Haiku não suporta a busca web com *dynamic filtering* — usa a variante básica, aceitável para enriquecimento leve. |
| SDR Argos | **Sonnet 5** (Opus para o argumento, se qualidade exigir) | Baixo volume (só promovidos), julgamento e argumento persuasivo. |

Alocar o modelo caro só **pós-promoção** é o que controla o custo — não se gasta o prospector nas centenas de leads crus que serão descartados na triagem.

### 3.3 Ferramentas do prospector (envelopam serviços existentes)

`consultar_benchmark`, `gerar_inteligencia`, `buscar_contato_verificado` (§6),
`propor_cadencia`, `gerar_roteiro_ligacao`, `atualizar_dossie` (grava no `Company`). Todas
read/draft; nenhuma dispara contato externo.

---

## 4. Modelo de dados (aditivo, enxuto)

O modelo de dois níveis + pós-promoção **dispensa uma tabela de propostas**. O output do
prospector são campos na `Company`, ao lado dos que o `CompanyAiService` já grava:

### `Company` — novos campos
```python
# além de resumo_executivo / proxima_acao_sugerida já existentes:
inteligencia_comercial: JSONB | None   # dossiê + benchmark + argumento (gerado direto aqui)
cadencia_sugerida:       JSONB | None   # sequence_id + contato + rascunhos (sugestão, não enrollment)
roteiro_ligacao:         Text  | None
sdr_atualizado_em:       timestamptz | None
sdr_custo_tokens:        Numeric | None # observabilidade de custo por empresa
```

### `LeadProspect` — sem mudança de sentido
Os campos de enriquecimento (setor, porte, decisor, etc.) continuam como estão; o aprendiz só os
preenche. **Remove-se** a necessidade de gerar/armazenar `inteligencia_comercial` no lead (agora
nasce na empresa) — ver decisão travada nº 5.

### Auditoria
Cada corrida do SDR Argos grava um `TimelineEvent` tipo `sdr` na empresa (o que fez, custo,
fontes). Sem tabela nova de proposta; a timeline já é o log auditável.

### Migração
Uma revisão Alembic (padrão `fb11856ce211_add_inteligencia_comercial.py`) adicionando as colunas
acima em `companies`. Sem backfill.

---

## 5. Backend & Frontend

### Backend
- **Aprendiz** — reusa `LeadEnrichmentService` (já existe); só adiciona o wiring do modelo barato
  e expõe o Fit no retorno. Task Celery de lote reusa o padrão de `import_lead_prospects_task`.
- **SDR Argos** — `app/services/sdr_argos.py`, o orquestrador (Tool Runner) que chama
  `CommercialIntelligenceService`, o provedor de contato (§6), monta cadência sugerida e roteiro,
  e grava no `Company`. Disparado (a) automaticamente na promoção via
  `LeadProspectService.promote` (mesmo gancho `after_commit` de `schedule_resumo_regeneration`),
  e (b) manualmente pelo botão.
- Endpoints: `POST /companies/{id}/sdr-argos` (re-rodar), leitura junto do `CompanyIcpRead` que
  já devolve o dossiê da empresa.

### Frontend
- **Pesquisa de Leads** — remove o botão "Inteligência Comercial"; mantém só "Enriquecer com IA"
  (individual + lote). Coluna de Fit já existe.
- **Empresas / Dossiê** — botão **"SDR Argos"** (re-rodar) ao lado do "Atualizar agora" do resumo.
  O dossiê da empresa passa a exibir argumento, cadência sugerida (com botão "Inscrever na
  cadência" que abre o form de enrollment pré-preenchido) e roteiro de ligação.

Pouca tela nova — é composição do que já existe, no espírito da Central de Leads.

---

## 6. Fonte de e-mail de contato — provedores de dados B2B (Apollo.io, Ramper e afins)

A busca web só encontra o que está **publicado**; e-mail de decisor nomeado quase nunca está.
Um provedor de dados de contato B2B é a forma **legítima** de resolver isso sem inventar
(decisão travada nº 7).

### 6.1 O que fazem (≠ busca web)
Mantêm um **banco proprietário de contatos B2B** e, na consulta, **verificam a entregabilidade**
(ping SMTP, catch-all), devolvendo um **status**: `verificado`, `provável`, `catch-all`,
`não encontrado`. O status `verificado` é dado de terceiro auditável — não é chute.

### 6.2 Escolha de provedor — o ICP muda a resposta
| | Apollo.io | Ramper | BR-nativos (Econodata, Speedio, Cortex, Leads2b) |
|---|---|---|---|
| Origem | EUA | Brasil | Brasil |
| Força | Base global, API robusta | Base BR, LinkedIn BR | Dado ancorado em CNPJ |
| Cobertura do ICP (embarcador industrial BR médio) | **Fraca** | Boa | Costuma cobrir melhor |

> **Waterfall enrichment:** nunca um só provedor. Tenta A; sem e-mail `verificado`, cai para B,
> depois C. O SDR Argos opera em cascata até ter verificado, ou desiste com `null`.

### 6.3 Guardrail por status
| Status | Ação do SDR Argos |
|---|---|
| `verificado` | E-mail entra; elegível a disparo (após confirmação de cadência) |
| `provável` / `catch-all` | Entra **marcado**; exige revisão humana |
| `não encontrado` | `null` + "sem e-mail confirmado" — nunca inventa |

### 6.4 LGPD e entregabilidade (pré-requisitos, não detalhe)
- **LGPD (bloqueante do disparo automático):** enriquecer e-mail de pessoa e disparar cadência
  tem base legal específica (tipicamente legítimo interesse) — finalidade clara, opt-out fácil,
  cuidado com dado nomeado. **Precisa passar pelo jurídico** antes de qualquer disparo autônomo.
- **Reputação de domínio:** disparar para e-mail duvidoso queima a reputação do domínio. Só
  disparar em `verificado` é guardrail de qualidade **e** de infraestrutura.

### 6.5 Custo e recomendação
Crédito/assinatura, tipicamente **centavos a ~R$ 1 por contato verificado**. Recomendação:
testar uma amostra real (~50 leads do ICP) em 2–3 provedores e comparar **taxa de verificado no
perfil de vocês** — é o único número que decide. Integrar como fonte com status (§6.3). Tratar
como **upgrade do enriquecimento**: agrega valor mesmo sem o agente.

---

## 7. Guardrails, risco e segurança (pré-requisito da autonomia)

1. **Teto de ações por sessão/tenant/dia** — máximo de e-mails/promoções por execução; sem isso
   um bug varre a base. (Análogo ao `max_uses` da busca web.)
2. **Anti-alucinação vira segurança** — decisão nº 7. Nenhum e-mail para contato não confirmado.
3. **Confirmação humana antes do 1º contato** — decisões nº 6 e 7. Disparo autônomo só em fase
   posterior, por flag, e só para alta confiança + fit alto.
4. **Descarte é aprendizado** — motivo guardado; taxa de correção/descarte autoriza (ou não) a
   autonomia.
5. **Auditoria total** — cada corrida grava `TimelineEvent` tipo `sdr`.
6. **Isolamento multi-tenant** — decisão nº 9; RLS + `ContextVar`. Em Managed Agents, credencial
   só via Cofre de credenciais.

---

## 8. O SDR Argos e a ligação: prepara, não fala

**Voz autônoma (bot que conversa com o prospect) fica fora de escopo** — em prospecção fria B2B
reprova nos critérios de regulatório (telemarketing/LGPD), disclosure, reputação de marca e custo
de erro (uma frase errada do bot já saiu e não se desfaz).

**O que o SDR Argos faz com a ligação** (reusando infra já paga):

| Etapa | Como | Já existe? |
|---|---|---|
| Roteiro de ligação personalizado | output do prospector a partir do dossiê | novo (trivial) |
| Criar a tarefa de ligação | `Task` tipo `ligacao` | ✅ |
| Discar + gravar | `twilio_voice.py` | ✅ |
| Transcrever | `transcribe_call_recording_task` + AssemblyAI | ✅ |
| Resumir + próxima ação pós-ligação | `CompanyAiService.regenerate_resumo` (já roda a cada evento) | ✅ |

O loop já está quase montado: a ligação transcrita já atualiza o resumo da conta hoje. O SDR
Argos só amarra as pontas (roteiro antes, entendimento depois).

---

## 9. Plano de desenvolvimento — prazo e custo

### 9.1 Fases e prazo (semanas de engenharia, 1 pessoa full-time)

| Fase | Entrega | Esforço |
|---|---|---|
| **0 — Piloto** | SDR Argos read-only (Managed Agents) sobre ~30 empresas promovidas reais: dossiê + argumento, sem escrever no CRM. Mede qualidade vs. humano. | **1–2 sem** |
| **1 — Aprendiz + handoff** | Wiring do modelo barato no "Enriquecer com IA" + Fit exposto; SDR Argos (Tool Runner) disparado na promoção, gravando dossiê/argumento/cadência-sugerida no `Company`; botão "SDR Argos" + inscrição de cadência confirmada. | **3–4 sem** |
| **2 — Contato verificado + ligação** | Integração do provedor B2B (§6, waterfall + guardrail por status) + roteiro de ligação + amarração do loop de transcrição. | **2–3 sem** |
| **3 — Autonomia supervisionada** | Flag por tenant para disparo sem confirmação em alta confiança; guardrails (§7); observabilidade custo/qualidade. **Só após jurídico (LGPD) e números da Fase 1.** | **2–3 sem** |

**Prazo:** piloto ~2 sem; produto usável (Fases 0+1) **~5–6 sem**; com contato verificado e
ligação (0–2) **~7–9 sem**; completo (0–3) **~9–12 sem**. O modelo de dois níveis reusa fortemente
o `CompanyAiService` e **dispensa a tabela/tela de fila** — um pouco mais enxuto que a proposta
monolítica original.

> Recomendação: **parar após a Fase 1 e operar 3–4 semanas** antes da autonomia. Disparo sem
> confirmação só depois de taxa de aprovação alta + jurídico ok.

### 9.2 Custo

**(a) Engenharia (uma vez)** — referência de **R$ 4.000–8.000/semana-engenheiro** (substituir
pela taxa real):

| Escopo | Semanas | Faixa (ref.) |
|---|---|---|
| Piloto (Fase 0) | 1–2 | R$ 4k–16k |
| Usável (0+1) | 5–6 | R$ 20k–48k |
| Com contato+ligação (0–2) | 7–9 | R$ 28k–72k |
| Completo (0–3) | 9–12 | R$ 36k–96k |

**(b) Operação (recorrente), por nível:**

| Item | Custo |
|---|---|
| Aprendiz (Haiku) por lead enriquecido | ~US$ 0,02–0,05 (R$ 0,10–0,27) |
| SDR Argos (Sonnet) por empresa promovida | ~US$ 0,30–0,50 (R$ 1,60–2,70) |
| Contato verificado (provedor B2B) | ~centavos a R$ 1 / contato |

A separação por nível é o que segura o custo: o item caro (SDR Argos + crédito de contato) só
incide **sobre empresas promovidas**, não sobre o volume de leads crus.

---

## 10. Métricas de sucesso do piloto

Antes da autonomia (Fase 3), o piloto precisa mostrar:
- **Taxa de aprovação** do dossiê/argumento do SDR Argos ≥ piso combinado (ex.: 70%).
- **Taxa de correção** (editado antes de usar) ≤ limite (ex.: 30%).
- **Qualidade do argumento** ≥ o que o vendedor escreveria (avaliação cega).
- **Taxa de e-mail `verificado`** no ICP suficiente para valer o provedor (§6.5).
- **Custo/empresa** dentro da faixa da §9.2.
- **Zero** contato inventado em auditoria.

---

## 11. Sequenciamento sugerido

1. **Fase 0** — piloto read-only (Managed Agents) sobre empresas promovidas; medir §10.
2. Decisão go/no-go.
3. **Fase 1** — aprendiz (modelo barato + Fit) na Pesquisa de Leads; SDR Argos no handoff da
   promoção, gravando no `Company`; botão + inscrição confirmada.
4. Operar 3–4 semanas.
5. **Fase 2** — provedor de contato verificado (§6) + roteiro/loop de ligação (§8).
6. **Fase 3** — autonomia supervisionada, **após jurídico (LGPD)** e números da Fase 1.
