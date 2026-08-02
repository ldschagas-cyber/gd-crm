# ✅ Checklist de QA Manual — CRM GD Conecta

Não há suite de testes de UI automatizada (só `tests/test_commercial_intelligence.py`
no backend). Este roteiro cobre teste manual de ponta a ponta. Rode sempre **como
admin e como usuário "vendedor"** nas seções marcadas com 👤👤 — várias telas têm
regra de permissão diferente por papel (já houve bug de `GET /users` admin-only
travando "Salvar" pra não-admin em 6 telas, corrigido mas vale reconfirmar a cada
rodada grande).

## 0. Ambiente

- [ ] `docker compose up --build` sobe sem erro (db, redis, api, worker, beat, frontend)
- [ ] `docker compose exec api python -m app.seed` cria tenant + admin
- [ ] `docker compose exec api pytest` — suíte existente passa
- [ ] Login com `admin@gdconecta.com.br` / `Admin@123456` funciona
- [ ] Criar um segundo usuário com papel "vendedor" (tela Usuários) pra testar permissões

## 1. Autenticação e permissões 👤👤

- [ ] Login com credencial errada → mensagem de erro clara, sem travar a tela
- [ ] Logout limpa sessão (voltar não reabre painel sem novo login)
- [ ] Como **vendedor**: abrir cada tela do menu e confirmar que "Salvar"/"Criar"
      funciona (não deve dar 403 silencioso — esse foi o bug anterior)
- [ ] Como **vendedor**: telas administrativas (Usuários, Configurações) devem
      estar ocultas ou bloqueadas, não quebradas

## 2. Núcleo comercial — Empresas / Contatos / Pipelines / Negócios / Tarefas

- [ ] Criar empresa manualmente (todos os campos obrigatórios + opcionais)
- [ ] Editar empresa existente, confirmar que a timeline registra a alteração
- [ ] Criar contato vinculado a uma empresa
- [ ] Abrir **Dossiê Comercial** da empresa (`CompanyDossierPage`): resumo por IA,
      score ICP e stack operacional carregam sem erro; testar com empresa **sem**
      dados suficientes (deve degradar graciosamente, não quebrar a tela)
- [ ] Pipelines: criar/editar estágio, arrastar negócio entre colunas no board
- [ ] Negócios: criar negócio, mudar de estágio, marcar como ganho/perdido
- [ ] Tarefas: criar tarefa vinculada a negócio/empresa, marcar concluída, prazo vencido aparece destacado

## 3. Dashboard

- [ ] Dashboard comercial (visão gestor): filtros de período, funil e SLA respondem e batem com os dados manuais que você criou
- [ ] Dashboard do vendedor (👤 login vendedor): mostra só os dados dele, não da equipe toda

## 4. Buscar Empresas

- [ ] Buscar por CNAE e por CNPJ retornam resultado esperado
- [ ] Faixa de funcionários não trunca (bug corrigido antes — reconfirmar)
- [ ] Importar/adicionar um resultado da busca como empresa no CRM

## 5. Pesquisa de Leads / Inteligência Comercial / Desempenho da Pesquisa

- [ ] Rodar pesquisa para um setor **mapeado** no Benchmark do Diagnóstico → mostra segmento e dado de frete
- [ ] Rodar para um setor **sem mapeamento** → degrada com mensagem, não erro 500
- [ ] Simular indisponibilidade do serviço de Diagnóstico (derrubar o backend do
      frete ou usar URL errada) → Pesquisa de Leads continua utilizável, só sem o cruzamento
- [ ] Tela "Desempenho da Pesquisa" reflete os resultados gerados acima

## 6. Formulários e Rastreio do site (item 9.8 — recém-implementado, testar fim a fim)

**Formulários**
- [ ] Criar formulário novo: montar campos por drag-and-drop, incluir 1 campo personalizado
- [ ] Salvar como "Rascunho" → botão de código de incorporação (`</>`) **não** aparece
- [ ] Mudar status para "Ativo" → botão de incorporação aparece; copiar o snippet
- [ ] Colar o snippet num HTML de teste local (fora do CRM) e abrir no navegador:
      formulário renderiza, envio grava em "Últimos envios" da tela e (se
      "Criar empresa/lead automaticamente" estiver ligado e o campo "Empresa"
      preenchido) gera lead novo em Empresas
- [ ] Reenviar com o mesmo CNPJ/nome de empresa → marca como "empresa já existente" (não duplica)
- [ ] Pausar o formulário e tentar enviar de novo pelo snippet já colado → deve rejeitar (mensagem de erro no formulário, não sucesso)
- [ ] KPIs do topo (ativos, envios 30d, conversão, leads gerados) batem com o que foi testado

**Rastreio do site**
- [ ] Copiar o snippet de rastreio (aba "Rastreio do site") e colar num HTML de teste
- [ ] Navegar por 2–3 páginas do HTML de teste → "Sessões por dia" e "Páginas mais visitadas" atualizam
- [ ] **Confirmar em ambiente de produção** que a URL gerada no snippet
      (`window.location.origin` + `/api/v1/...`) realmente resolve — abra a URL do
      `track.js` direto no navegador a partir de `https://crm.gdconecta.com.br` e
      confira que retorna JavaScript (200), não 404. Isso não foi validado nesta
      revisão e a lógica de montagem da URL assume um padrão de porta que pode
      não bater com o proxy central em produção.
- [ ] Sem `IPINFO_API_TOKEN` configurado (é o caso hoje): confirmar que "Empresas
      identificadas" fica vazio sem quebrar a tela, e que sessões/páginas continuam
      contando normalmente
- [ ] Exportar CSV da aba Rastreio e abrir o arquivo (checar acentuação/encoding)

## 7. Motor de outbound — Sequências / Cadências / Modelos de E-mail / Snippets / Workflows

- [ ] Criar modelo de e-mail com variáveis (nome, empresa) e conferir substituição no preview
- [ ] Criar sequência com 2–3 passos, associar a um lead, confirmar que o e-mail
      realmente é enviado via Microsoft Graph (checar caixa de saída), não só a
      tarefa manual de fallback
- [ ] Cadência: mesmo teste, confirmar disparo automático no horário configurado
- [ ] Snippets: inserir um snippet salvo dentro de um e-mail/tarefa
- [ ] Workflows: disparar a condição configurada (ex.: mudança de estágio) e confirmar a ação automática

## 8. Usuários / Preferências / Configurações

- [ ] Preferências: upload de foto de perfil funciona e aparece no topo da tela
- [ ] Conectar E-mail/Calendário via Microsoft Graph, confirmar que o token persiste após logout/login
- [ ] Usuários: criar, editar papel, desativar usuário (👤 confirmar que vendedor não acessa esta tela)
- [ ] Configurações: alterar algo (ex. dado do tenant) e confirmar persistência

## 9. Regressão / isolamento multi-tenant

- [ ] Criar um segundo tenant (se aplicável no seu ambiente de teste) e confirmar
      que dados de um tenant **nunca** aparecem pro outro (empresas, negócios, formulários, rastreio)
- [ ] Testar em aba anônima/incógnito pra garantir que não há vazamento de sessão entre logins diferentes

## Registro de achados

Pra cada item que falhar: anotar tela, passo exato, resultado esperado vs. obtido,
e se é bloqueante pra liberar pro primeiro cliente pagante ou pode esperar.
