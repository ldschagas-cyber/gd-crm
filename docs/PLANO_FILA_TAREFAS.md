# Plano — Execução sequencial de tarefas ("fila de tarefas")

Status: **proposta / não implementado**. Este documento e o protótipo em
`docs/prototypes/fila_tarefas_prototype.html` existem para alinhar o desenho antes
de codar. Nada aqui foi construído na aplicação real ainda.

## Contexto

Hoje `Tarefas` (`frontend/src/pages/TarefasPage.jsx`) é uma agenda: lista plana
agrupada por data, com checkbox de concluir por linha. Não existe um jeito de
"tocar" a lista tarefa a tarefa, nem um painel que muda de acordo com o tipo da
tarefa (ligação, e-mail, etc.) — quem cria/edita uma tarefa vê sempre o mesmo
formulário genérico (`TaskModal`, linhas 223–359 do mesmo arquivo).

O print de referência que motivou o pedido é do HubSpot (o rodapé "Breeze
Assistant" denuncia — não é print do nosso produto), usado aqui como inspiração
de fluxo, não como especificação a copiar 1:1.

## Duas melhorias pedidas

1. Um modo de **executar as tarefas de uma lista, uma a uma**, abrindo
   automaticamente a ação certa pro tipo da tarefa (discador pra ligação,
   composer pra e-mail).
2. Ao abrir o discador de uma tarefa de ligação, **mostrar o script/roteiro da
   ligação** junto.

## Decisões já tomadas com o Daniel

| Pergunta | Decisão |
|---|---|
| De onde vem o script de ligação? | **Reaproveitar o Snippets** (`SnippetsPage.jsx`, model `Snippet`) — sem tabela nova. Ver seção dedicada abaixo. |
| Quais tarefas entram na fila? | A **lista filtrada atual** da tela Tarefas — respeita os filtros já aplicados (responsável, data, tipo etc.), sem tela extra de seleção. |
| O que fazer com tipos sem ação especial (WhatsApp, reunião, LinkedIn, tarefa manual, follow-up)? | **Painel genérico**: roteiro + dados do contato + Concluir/Pular. Sem integração especial na v1 (ex.: link `wa.me` automático fica pra depois — o padrão já existe em `ContatosPage.jsx`/`CompanyDetailPage.jsx` e é fácil de plugar depois). |
| A fila avança sozinha depois de concluir a ação? | **Não.** Espera clique em "Próxima" — o usuário revisa antes de avançar. |

## Melhoria 1 — Fila de execução

### Entrada
Botão **"Iniciar tarefas"** no cabeçalho da `TarefasPage`, ao lado dos filtros
existentes (`page-actions`, linha ~332). Abre sobre a lista filtrada atual, na
mesma ordem já exibida (data/hora). Texto do botão mostra a contagem, ex.:
"Iniciar 28 tarefas" — só conta as pendentes do filtro atual.

### Tela da fila (overlay full-screen, nova rota `/tarefas/executar`)
Cabeçalho fixo:
- `< Tarefas` — fecha a fila, volta pra lista.
- Nome do contato/empresa da tarefa atual (equivalente ao "Demonstração" do print).
- Contador **Tarefa N/Total** com setas anterior/próxima — navegação livre,
  não força concluir pra andar.
- Checkbox **Concluído**, refletindo `task.status`.
- `X` fecha.

Corpo em duas colunas:
- **Coluna esquerda — contexto**: cartão do contato/empresa/negócio associado
  (nome, telefone, e-mail, link pra ficha completa) + roteiro da tarefa
  (`task.descricao`, ver Melhoria 2) com botão de inserir snippet.
- **Coluna direita — ação**, muda conforme `task.tipo`:
  - **`ligacao`**: botão Ligar (`useSoftphone().call()`), status ao vivo
    (idle/discando/chamando/em chamada), e ao encerrar: campo de resultado
    (atendeu / caixa postal / não atendeu / número errado — **a definir**, ver
    riscos) + "Concluir tarefa".
  - **`email`**: composer com Para/Assunto/Corpo, seletor de **Modelos**
    (`EmailTemplate`, já existe e já é usado por Sequências), inserir snippet,
    botão "Enviar e concluir tarefa".
  - **demais tipos**: painel genérico (roteiro + dados do contato) com
    "Concluir" / "Pular".

Rodapé: "Marcar como completo" / "Marcar como incompleto" (útil pra tipos sem
ação automática, e pra desfazer engano) e "Próxima" separado (sem
auto-avanço).

Ao fechar ou terminar a última tarefa: volta pra lista com um toast
"X de Y tarefas concluídas".

### Impacto técnico (resumo, pra dimensionar depois)
- Frontend: rota/overlay novo + componente `TaskQueuePanel` que despacha por
  `tipo` (não existe hoje — confirmado na exploração, o único lugar que já
  varia campos por tipo é o `TimelineComposer.jsx`, mas é pra notas soltas,
  não tarefas).
- Backend: falta endpoint pra **desmarcar conclusão** (hoje só existe
  `PATCH /tasks/{id}/complete` em `app/api/v1/tasks.py`, sem volta).
- Envio de e-mail manual pela fila precisa de endpoint novo (ex.:
  `POST /tasks/{id}/send-email`) reaproveitando `GraphClient.send_mail` — hoje
  esse client só é chamado pelo envio automático de Sequências
  (`app/services/sequence_dispatch.py`). Só funciona pra quem já conectou a
  conta Microsoft 365 em Preferências → E-mail; sem isso, precisa de
  fallback (ex.: abrir `mailto:` ou avisar pra conectar a integração).
- Registro de ligação: hoje o Softphone/Twilio já grava um `Call` via webhook
  (duração, sid). Não confirmei se algum campo de **resultado/outcome**
  humano (atendeu, caixa postal etc.) já existe em algum lugar — se não
  existir, é campo novo em `Call` ou em `TimelineEvent`.

## Melhoria 2 — Script de ligação via Snippets

Ideia do próprio Daniel, e encaixa bem no que já existe: **não cria modelo
novo**. O "roteiro" mostrado na fila continua sendo o campo
`Descrição / roteiro` da tarefa (`Task.descricao`) — esse campo já existe hoje
e o placeholder atual já diz "Roteiro / instruções para quem for executar…",
só que hoje ninguém o exibe de volta como painel de script.

Pra facilitar escrever esse roteiro a partir de blocos reutilizáveis:
- Adicionar ao campo de roteiro (tanto no `TaskModal` quanto no painel da
  fila) a mesma mecânica de expansão que já existe em `SnippetsPage.jsx`
  (digitar `#atalho` + espaço expande o conteúdo do snippet) — hoje essa
  expansão só está ligada na textarea de demonstração da própria página de
  Snippets, precisa ser generalizada pra outros campos de texto do CRM
  (é o que o texto de ajuda da página já promete: "insira em notas, tarefas
  ou qualquer campo de texto do CRM" — hoje isso não é verdade ainda em
  Tarefas).
- No painel de ligação da fila, o roteiro é exibido com as variáveis
  `{{nome}}`, `{{empresa}}`, `{{cargo}}`, `{{responsavel}}` já mescladas com
  os dados reais do contato daquela tarefa — reaproveitando a mesma lógica de
  merge que já existe em `SnippetsPage.mergeVars` (frontend) e
  `sequence_dispatch.render_template` (backend, hoje só usada pra e-mail).

Sem integração nova, sem aprovação, sem tabela nova — só reaproveitamento de
dado e extensão de um recurso que já existe. Se no futuro fizer sentido
separar "snippets de script de ligação" dos demais snippets, dá pra adicionar
um campo opcional `categoria` no model `Snippet` (hoje só tem
`nome/atalho/conteudo`) pra filtrar/sugerir os certos — não necessário pra v1.

## Decisões dos pontos em aberto (rodada 2)

1. **Endpoint de "desmarcar conclusão"** — confirmado: criar
   `PATCH /tasks/{id}/uncomplete` no backend (`app/api/v1/tasks.py` +
   `app/services/task.py`), espelhando o `complete` que já existe (limpa
   `status`/`concluida_em`).
2. **Envio manual de e-mail sem integração conectada** — confirmado: o painel
   de e-mail da fila detecta se o responsável tem a integração Microsoft 365
   ativa (mesma checagem que `has_active_email_integration` já faz em
   `sequence_dispatch.py`). Se **não** tiver: mostra aviso pra conectar em
   Preferências → E-mail, e o botão vira **"Abrir no meu e-mail"**, que monta
   um link `mailto:` (destinatário, assunto e corpo já preenchidos) como
   fallback — a tarefa não se conclui sozinha nesse caso, o vendedor confirma
   manualmente que enviou.
3. **Resultado da ligação (outcome)** — confirmado: criar do zero. Lista
   inicial proposta (desfechos padrão de mercado, ajustável):
   - Atendeu
   - Deixou recado / caixa postal
   - Não atendeu
   - Ocupado
   - Número errado / inexistente
   - Recusou falar

   Fica salvo num campo novo `resultado_ligacao` (enum) no `Task` — só
   preenchido quando `tipo = ligacao`, gravado junto com a conclusão da
   tarefa (`PATCH /tasks/{id}/complete` passa a aceitar esse campo opcional
   no payload). Precisa de migration Alembic nova, no mesmo padrão de
   `a3f6c1d9e2b7_add_descricao_to_tasks.py`.

## Ainda em aberto

4. **Expansão de snippet em qualquer textarea** — pré-requisito de
   engenharia pra Melhoria 2 (não é uma decisão de produto): hoje `#atalho` +
   espaço só funciona na demonstração da própria página de Snippets, precisa
   ser generalizado pro campo de Roteiro (`TaskModal` e painel da fila).

## Roteiro por IA — decidido: fica pra depois (v1.1)

A v1 da fila sai só com roteiro manual (`Task.descricao`) + Snippets pra
inserir blocos reutilizáveis — nada de IA nessa primeira entrega.

Quando entrar, a ideia é reaproveitar o padrão já existente em
`company_ai.py` (mesma conta Anthropic, mesmo `_contexto()` de empresa —
segmento, fit ICP, ERP/TMS, problemas encontrados, negócios, timeline
recente) pra gerar um rascunho de roteiro de ligação considerando o motivo
específico da tarefa, editável, com Snippets ainda disponíveis por cima pra
blocos fixos (política de desconto, disclaimers) que a IA não deveria
improvisar. Cacheado no próprio `descricao` da tarefa, regenerado só sob
demanda, pra não gastar uma chamada de API a cada abertura da fila.

## Situação adicional — Transcrição de ligação na timeline

Retomando algo discutido numa sessão anterior: "baixar a transcrição da
ligação pra timeline" **já está construído**, não é mais decisão de produto —
é ativação/blindagem de um pipeline que existe de ponta a ponta e nunca foi
ligado.

O que já existe:
- Toda ligação Twilio já é gravada hoje (`record="record-from-answer"`,
  `app/services/twilio_voice.py`).
- Ao terminar, dispara Celery → sobe pra **AssemblyAI** (PT-BR, diarização,
  redação de PII) → webhook de conclusão grava o texto no `TimelineEvent` e
  **apaga o áudio dos dois lados** (só o texto fica retido — decisão de
  produto já tomada e documentada no código,
  `app/services/assemblyai_transcription.py`).
- O frontend já renderiza — "Ver transcrição" expansível na timeline
  (`CompanyDetailPage.jsx:234`, também em ContactDetailPage/DealDetailPage),
  com tag de erro se falhar.

Falta pra funcionar de verdade:

1. **`ASSEMBLYAI_API_KEY` / `ASSEMBLYAI_WEBHOOK_SECRET`** não estão nem
   documentadas em `.env.example` — sinal forte de que nunca foi configurada
   em produção. Precisa criar conta na AssemblyAI e setar a chave no servidor.
2. **Sem gate de `is_configured()`** — hoje, sem a chave, a task Celery
   estoura exceção a cada ligação gravada, em vez de falhar bonito (o padrão
   já usado pra e-mail em `has_active_email_integration` deveria se repetir
   aqui).
3. **Sem visibilidade** — a aba Preferências → Chamadas não mostra se a
   transcrição está ativa.
4. **Aviso de gravação pro cliente** — não há `<Say>` (nem outro aviso)
   informando que a ligação pode ser gravada, nem na saída nem na entrada.
   **Pergunta em aberto pro Daniel**: isso já foi validado com jurídico/LGPD,
   ou precisa entrar no escopo?

Conexão com a fila de tarefas: não muda o desenho das Melhorias 1/2 — depois
de uma ligação feita pela fila, a transcrição chega sozinha na timeline
depois (assíncrono), sem precisar de nada novo no painel de ligação.

## Protótipo

Ver `docs/prototypes/fila_tarefas_prototype.html` — HTML estático no mesmo
padrão visual dos outros protótipos da pasta (`tarefas_prototype.html` etc.),
com um seletor de demonstração pra alternar entre os três estados do painel
direito (Ligação / E-mail / Outro tipo) e ver o roteiro com snippet mesclado.
