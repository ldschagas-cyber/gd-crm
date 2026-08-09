
  var TODAY = new Date('2026-08-05T12:00:00');

  var CATEGORIAS = [
    { id: 'processo',    nome: 'Processo Comercial', color: 'var(--azul)',      desc: 'Etapas do processo de venda, SLAs, o que fazer em cada fase' },
    { id: 'script',      nome: 'Scripts',            color: 'var(--indigo-600)',desc: 'Roteiros de abordagem — ligação, e-mail, WhatsApp' },
    { id: 'objecao',     nome: 'Objeções',           color: 'var(--serious)',   desc: 'Objeção do prospect + como responder' },
    { id: 'case',        nome: 'Cases',              color: 'var(--good)',      desc: 'Case real de cliente — problema, solução, resultado' },
    { id: 'metodologia', nome: 'Metodologia',        color: 'var(--amber)',     desc: 'Frameworks de venda — qualificação, descoberta, etc.' },
  ];
  var CAT_BY_ID = {};
  CATEGORIAS.forEach(function (c) { CAT_BY_ID[c.id] = c; });

  var SETORES = ['Geral', 'Farma', 'Alimentos', 'Autopeças', 'Química', 'Etiquetas', 'Plástico', 'Máquinas e Equipamentos', 'Cosmético', 'Varejo'];

  var USERS = { FN: 'Felipe Nogueira', MD: 'Marina Duarte', CR: 'Camila Rezende', PL: 'Paula Lemos', DC: 'Daniel Chagas' };

  function daysAgo(n) { var d = new Date(TODAY); d.setDate(d.getDate() - n); return d; }
  function fmtRelative(date) {
    var days = Math.floor((TODAY - date) / 86400000);
    if (days <= 0) return 'hoje';
    if (days === 1) return 'ontem';
    if (days < 7) return 'há ' + days + ' dias';
    if (days < 30) return 'há ' + Math.floor(days / 7) + ' semana(s)';
    if (days < 365) return 'há ' + Math.floor(days / 30) + ' mês(es)';
    return 'há ' + Math.floor(days / 365) + ' ano(s)';
  }
  function daysSince(date) { return Math.floor((TODAY - date) / 86400000); }
  function escapeHtml(s) { return (s || '').replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }

  // ---------------- Markdown leve: **negrito**, "- item" -> lista, "## " -> h4 ----------------
  function inline(s) { return escapeHtml(s).replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>'); }
  function renderMd(md) {
    var blocks = (md || '').split(/\n\s*\n/);
    return blocks.map(function (block) {
      var lines = block.split('\n').filter(function (l) { return l.trim() !== ''; });
      if (lines.length === 0) return '';
      if (/^##\s+/.test(lines[0]) && lines.length === 1) return '<h4>' + inline(lines[0].replace(/^##\s+/, '')) + '</h4>';
      if (lines.every(function (l) { return /^\s*-\s+/.test(l); })) {
        return '<ul>' + lines.map(function (l) { return '<li>' + inline(l.replace(/^\s*-\s+/, '')) + '</li>'; }).join('') + '</ul>';
      }
      return '<p>' + lines.map(inline).join('<br>') + '</p>';
    }).join('');
  }

  // ---------------- Mock dataset ----------------
  var seq = 0;
  function art(o) { seq++; return Object.assign({ id: 'a' + seq, tags: '', util_positivo: 0, util_negativo: 0, visualizacoes: 0, status: 'publicado', autor: 'DC' }, o); }

  var ARTICLES = [
    art({ categoria: 'processo', titulo: 'Processo comercial: da Central de Leads ao fechamento', setor: 'Geral',
      resumo: 'As 6 etapas do funil e o que fazer (e não fazer) em cada uma.',
      tags: 'processo,funil,sla',
      conteudo: '## Visão geral\nO funil tem 6 etapas: Novo, Qualificando, Cadência, MQL, SQL e Convertido. MQL e SQL **nunca** são automáticos — sempre exigem confirmação humana.\n\n## O que fazer em cada etapa\n- **Novo**: validar dados de contato e confirmar setor/porte antes de qualquer abordagem.\n- **Qualificando**: fazer a primeira ligação de descoberta em até 24h — leads esfriam rápido.\n- **Cadência**: acompanhar aberturas de e-mail; se não engajar em 3 tentativas, ir para reativação.\n- **MQL**: priorizar contato humano na semana — engajamento alto sem contato é oportunidade perdida.\n- **SQL**: preparar proposta em até 48h do sinal de compra.',
      atualizado: daysAgo(12), util_positivo: 18, util_negativo: 1, visualizacoes: 140 }),

    art({ categoria: 'script', titulo: 'Ligação fria — abertura em 30 segundos', setor: 'Geral',
      resumo: 'Roteiro de abertura pra primeira ligação com um lead que nunca ouviu falar da gente.',
      tags: 'ligação,cold call,abertura',
      conteudo: '## Abertura\n"Oi, [nome], aqui é [seu nome] da Argos. Te liguei porque [motivo específico — não genérico]. Tenho só 30 segundos, tudo bem?"\n\n## Se a pessoa topar\n- Confirmar 1 dor específica do setor antes de falar de produto.\n- Perguntar quem mais participa da decisão de transporte/frete.\n- Fechar pedindo 20 minutos numa data específica — nunca "quando puder".\n\n## Se a pessoa cortar\n"Sem problema — posso mandar 1 e-mail curto com o que eu ia falar?" (sempre peça permissão pro follow-up, não insista na ligação).',
      atualizado: daysAgo(5), util_positivo: 24, util_negativo: 2, visualizacoes: 210 }),

    art({ categoria: 'script', titulo: 'E-mail de reativação — base fria há 90+ dias', setor: 'Geral',
      resumo: 'Modelo curto pra reabrir conversa com lead que parou de responder.',
      tags: 'email,reativação',
      conteudo: '## Quando usar\nLead sem interação há 90 dias ou mais, cadência anterior esgotada sem resposta.\n\n## Modelo\n"Assunto: ainda faz sentido pra vocês?\n\nOi [nome], faz um tempo que não conversamos sobre [tema]. Sei que prioridade muda — ainda faz sentido explorar isso este trimestre, ou prefere que eu volte a falar daqui uns meses?"\n\n- Curto de propósito — a pergunta é o gancho, não o argumento.\n- Se não responder em 5 dias úteis, mover pra "reengajamento anual" e não insistir mais.',
      atualizado: daysAgo(140), util_positivo: 9, util_negativo: 3, visualizacoes: 88 }),

    art({ categoria: 'objecao', titulo: '"Já temos transportadora fixa, não trocamos"', setor: 'Geral',
      resumo: 'Objeção mais comum na abordagem inicial — como não entrar em confronto direto.',
      tags: 'objeção,preço,transportadora',
      conteudo: '## O que a pessoa está dizendo de verdade\nNa maioria das vezes não é "não preciso", é "trocar dá trabalho e risco". Não é uma objeção de preço.\n\n## Como responder\n"Faz todo sentido — a maioria dos nossos clientes também tinha transportadora fixa. A gente não entra pra substituir, entra pra dar visibilidade e cotação sobre o que já roda — muita gente descobre 15-20% de economia sem trocar de transportadora, só organizando a cotação."\n\n- Nunca ataque a transportadora atual do cliente.\n- Peça 1 dado concreto (nº de CT-e/mês) pra ancorar o benchmark do setor.',
      atualizado: daysAgo(30), util_positivo: 31, util_negativo: 1, visualizacoes: 265 }),

    art({ categoria: 'objecao', titulo: '"Não tenho orçamento agora"', setor: 'Geral',
      resumo: 'Como separar objeção de timing real de desculpa educada.',
      tags: 'objeção,orçamento,timing',
      conteudo: '## Diagnosticar antes de responder\nPergunte: "Isso é uma questão de prioridade ou de o orçamento já estar fechado pro ano?" — a resposta muda totalmente a estratégia.\n\n## Se for prioridade\nTraga o benchmark de custo/kg do setor pra virar prioridade de novo.\n\n## Se for orçamento fechado\nNão insista em fechar agora. Agende retomada pro início do próximo ciclo orçamentário e mantenha em cadência de nutrição — forçar aqui queima o relacionamento.',
      atualizado: daysAgo(75), util_positivo: 14, util_negativo: 0, visualizacoes: 120 }),

    art({ categoria: 'objecao', titulo: '"Seu sistema não integra com nosso ERP"', setor: 'Farma',
      resumo: 'Objeção técnica comum no setor Farma, onde ERPs legados são a norma.',
      tags: 'objeção,integração,erp,farma',
      conteudo: '## Contexto do setor\nDistribuidoras de Farma costumam rodar ERPs antigos (às vezes desenvolvidos internamente) — integração é preocupação legítima, não desculpa.\n\n## Como responder\n"Entendo — a maioria dos nossos clientes de Farma também tinha essa dúvida. A gente não exige substituir o ERP: dá pra rodar em paralelo via planilha/e-mail no início e evoluir pra integração depois, sem travar o começo."\n\n- Cite o case da Vale Verde (ver Cases) se o prospect for do mesmo porte.',
      atualizado: daysAgo(20), util_positivo: 11, util_negativo: 0, visualizacoes: 74 }),

    art({ categoria: 'case', titulo: 'Case: Farmacêutica Vale Verde — 18% de economia em 4 meses', setor: 'Farma',
      resumo: 'Do diagnóstico ao resultado — use quando o prospect for do mesmo porte/setor.',
      tags: 'case,farma,economia',
      conteudo: '## Problema\nDistribuidora regional de Farma, ~180 funcionários, sem visibilidade de custo/kg entre transportadoras diferentes por região.\n\n## Solução\nBenchmark Logístico + cotação centralizada, sem trocar transportadora nos primeiros 2 meses.\n\n## Resultado\n**18% de economia em custo/kg** em 4 meses, mantendo o mesmo nível de serviço — usado pra renegociar contrato com a transportadora principal, não pra substituí-la.\n\n## Quando citar\nProspects de Farma/distribuição com múltiplas transportadoras regionais e sem cotação centralizada hoje.',
      atualizado: daysAgo(8), util_positivo: 22, util_negativo: 0, visualizacoes: 190 }),

    art({ categoria: 'case', titulo: 'Case: Grupo Andrade Embalagens — piloto de 30 dias', setor: 'Etiquetas',
      resumo: 'Bom exemplo pra prospect que pede "prova antes de comprometer o ano todo".',
      tags: 'case,piloto,etiquetas',
      conteudo: '## Problema\nEmpresa de etiquetas relutante em assinar contrato anual sem ver resultado primeiro.\n\n## Solução\nPiloto de 30 dias numa única filial, sem custo de setup, com relatório comparativo ao final.\n\n## Resultado\nApós o piloto, expandiu para as 3 filiais e fechou contrato anual — o piloto reduziu o risco percebido sem a gente precisar baixar preço.',
      atualizado: daysAgo(200), util_positivo: 6, util_negativo: 1, visualizacoes: 55 }),

    art({ categoria: 'metodologia', titulo: 'Framework de qualificação — GD-FIT', setor: 'Geral',
      resumo: 'Adaptação do BANT pro nosso produto: Frequência, Impacto, Timing.',
      tags: 'metodologia,qualificação,bant',
      conteudo: '## As 3 perguntas\n- **Frequência**: quantos CT-e/mês a empresa emite ou recebe? (abaixo de 50/mês, o ROI é fraco)\n- **Impacto**: quem sente a dor hoje — logística, financeiro ou diretoria? Quanto mais alto, mais rápido fecha.\n- **Timing**: existe gatilho concreto (expansão, troca de transportadora, reclamação recente) ou é "seria bom ter"?\n\n## Como pontuar\nUse a régua de Lead Score (Fit ICP + Engajamento) da Central de Leads — este framework serve pra guiar a conversa de descoberta, não substitui o score automático.',
      atualizado: daysAgo(45), util_positivo: 19, util_negativo: 2, visualizacoes: 133 }),

    art({ categoria: 'metodologia', titulo: 'Descoberta em 5 perguntas antes de propor preço', setor: 'Geral',
      resumo: 'Evita a maior causa de proposta rejeitada: apresentar preço sem entender o cenário.',
      tags: 'metodologia,descoberta',
      conteudo: '- Quantas transportadoras vocês usam hoje?\n- Como é feita a cotação hoje — planilha, e-mail, sistema?\n- Quem aprova a escolha de transportadora numa entrega nova?\n- Já tiveram problema de atraso/avaria que gerou custo extra recente?\n- O que faria essa decisão ser prioridade este trimestre?',
      atualizado: daysAgo(60), util_positivo: 15, util_negativo: 0, visualizacoes: 98 }),

    art({ categoria: 'script', titulo: 'WhatsApp — follow-up pós-reunião de descoberta', setor: 'Geral',
      resumo: 'Mensagem curta pra manter o ritmo sem parecer robótico.',
      tags: 'whatsapp,follow-up',
      conteudo: '"Oi [nome], obrigado pelo tempo hoje! Vou preparar [o que foi combinado] e te mando até [dia]. Fica algo pendente da nossa parte além disso?"\n\n- Sempre reafirme prazo e próximo passo — reunião sem follow-up em 24h esfria.',
      atualizado: daysAgo(3), util_positivo: 8, util_negativo: 0, visualizacoes: 61, status: 'rascunho', autor: 'CR' }),

    art({ categoria: 'objecao', titulo: '"Vou conversar com meu sócio e te retorno"', setor: 'Varejo',
      resumo: 'Comum em empresas de varejo de porte menor com decisão compartilhada.',
      tags: 'objeção,decisor,varejo',
      conteudo: '"Faz sentido! Pra eu ajudar nessa conversa, consigo te mandar um resumo de 1 página com o número principal — assim vocês dois já discutem com o dado em mãos. Quando seria um bom dia pra eu retomar contigo?"\n\n- Sempre feche com uma data, não um "te aviso".',
      atualizado: daysAgo(2), util_positivo: 2, util_negativo: 0, visualizacoes: 14, status: 'rascunho', autor: 'PL' }),

    art({ categoria: 'processo', titulo: 'SLA de resposta por etapa do funil', setor: 'Geral',
      resumo: 'Tempos máximos de resposta — referência rápida de time de vendas.',
      tags: 'sla,processo',
      conteudo: '- **Novo → primeiro contato**: até 24h úteis\n- **Reunião realizada → follow-up**: até 24h\n- **Proposta enviada → checagem de leitura**: até 48h\n- **SQL sem negócio aberto há 7 dias**: escalar para o gestor',
      atualizado: daysAgo(400), util_positivo: 5, util_negativo: 4, visualizacoes: 300 }),

    art({ categoria: 'case', titulo: 'Case antigo: Metalúrgica (descontinuado)', setor: 'Máquinas e Equipamentos',
      resumo: 'Case fora de uso — cliente encerrou contrato; manter só de referência histórica.',
      tags: 'case,arquivado',
      conteudo: 'Case arquivado após encerramento de contrato em 2025. Não usar em abordagem — mantido só pra referência interna de histórico.',
      atualizado: daysAgo(500), util_positivo: 1, util_negativo: 2, visualizacoes: 40, status: 'arquivado' }),
  ];

  // ---------------- Estado ----------------
  var state = { role: 'admin', screen: 'lib', categoria: '', setor: '', busca: '', myVotes: {} };

  var roleSwitch = document.getElementById('roleSwitch');
  roleSwitch.addEventListener('click', function (e) {
    var btn = e.target.closest('button[data-role]');
    if (!btn) return;
    state.role = btn.dataset.role;
    Array.prototype.forEach.call(roleSwitch.children, function (b) { b.classList.toggle('active', b === btn); });
    if (state.role === 'vendedor') {
      document.getElementById('sbName').textContent = 'Camila Rezende';
      document.getElementById('sbRole').textContent = 'Vendedor · GD Conecta';
      document.getElementById('sbAvatar').textContent = 'CR';
    } else {
      document.getElementById('sbName').textContent = 'Daniel Chagas';
      document.getElementById('sbRole').textContent = 'Admin · GD Conecta';
      document.getElementById('sbAvatar').textContent = 'DC';
    }
    renderAll();
  });

  var screenSwitch = document.getElementById('screenSwitch');
  screenSwitch.addEventListener('click', function (e) {
    var btn = e.target.closest('button[data-screen]');
    if (!btn) return;
    state.screen = btn.dataset.screen;
    Array.prototype.forEach.call(screenSwitch.children, function (b) { b.classList.toggle('active', b === btn); });
    document.getElementById('screenLib').style.display = state.screen === 'lib' ? '' : 'none';
    document.getElementById('screenDossier').style.display = state.screen === 'dossier' ? '' : 'none';
    if (state.screen === 'dossier') renderDossierPreview();
  });

  // setor filter options
  var setorSel = document.getElementById('setorFilter');
  setorSel.innerHTML += SETORES.map(function (s) { return '<option value="' + s + '">' + s + '</option>'; }).join('');
  setorSel.addEventListener('change', function () { state.setor = setorSel.value; renderGrid(); });
  document.getElementById('searchInput').addEventListener('input', function (e) { state.busca = e.target.value.toLowerCase(); renderGrid(); });

  function isVisible(a) {
    // Vendedor só vê publicados + seus próprios rascunhos.
    if (state.role === 'vendedor') return a.status === 'publicado' || (a.status === 'rascunho' && a.autor === 'CR');
    return true;
  }

  function passesFilter(a) {
    if (!isVisible(a)) return false;
    if (state.categoria && a.categoria !== state.categoria) return false;
    if (state.setor && a.setor !== state.setor) return false;
    if (state.busca) {
      var hay = (a.titulo + ' ' + a.tags + ' ' + a.resumo).toLowerCase();
      if (hay.indexOf(state.busca) === -1) return false;
    }
    return true;
  }

  function renderCatTabs() {
    var counts = {};
    ARTICLES.filter(isVisible).forEach(function (a) { counts[a.categoria] = (counts[a.categoria] || 0) + 1; });
    var total = ARTICLES.filter(isVisible).length;
    var html = '<div class="cat-tab' + (state.categoria === '' ? ' active' : '') + '" data-cat="" style="--cat-color: var(--indigo);"><span class="d"></span>Todos <span class="n">' + total + '</span></div>';
    html += CATEGORIAS.map(function (c) {
      var n = counts[c.id] || 0;
      return '<div class="cat-tab' + (state.categoria === c.id ? ' active' : '') + '" data-cat="' + c.id + '" style="--cat-color: ' + c.color + ';" title="' + escapeHtml(c.desc) + '"><span class="d"></span>' + c.nome + ' <span class="n">' + n + '</span></div>';
    }).join('');
    var el = document.getElementById('catTabs');
    el.innerHTML = html;
    Array.prototype.forEach.call(el.querySelectorAll('.cat-tab'), function (t) {
      t.addEventListener('click', function () { state.categoria = t.dataset.cat; renderCatTabs(); renderGrid(); });
    });
  }

  function renderStats() {
    var visible = ARTICLES.filter(isVisible);
    var publicados = visible.filter(function (a) { return a.status === 'publicado'; }).length;
    var pendentes = ARTICLES.filter(function (a) { return a.status === 'rascunho'; }).length;
    var stale = visible.filter(function (a) { return a.status !== 'arquivado' && daysSince(a.atualizado) >= 90; }).length;
    var totalVotos = visible.reduce(function (s, a) { return s + a.util_positivo + a.util_negativo; }, 0);
    var totalPos = visible.reduce(function (s, a) { return s + a.util_positivo; }, 0);
    var pctUtil = totalVotos ? Math.round((totalPos / totalVotos) * 100) : 0;

    document.getElementById('headTotal').textContent = publicados;
    document.getElementById('headPending').textContent = pendentes;
    document.getElementById('headStale').textContent = stale;

    var tiles = [
      { t: 'Publicados', v: publicados, cls: '' },
      { t: 'Rascunhos p/ revisar', v: pendentes, cls: 'pending', clickable: state.role === 'admin' },
      { t: 'Sem revisão 90+ dias', v: stale, cls: 'stale', clickable: true },
      { t: '% achou útil', v: pctUtil + '%', cls: 'good' },
      { t: 'Setores cobertos', v: (new Set(visible.map(function (a) { return a.setor; }))).size, cls: '' },
    ];
    document.getElementById('statStrip').innerHTML = tiles.map(function (s) {
      return '<div class="stat-tile ' + s.cls + (s.clickable ? ' clickable' : '') + '" data-tile="' + s.t + '"><div class="t">' + s.t + '</div><div class="v">' + s.v + '</div></div>';
    }).join('');
    var staleTile = document.querySelector('.stat-tile.stale');
    if (staleTile) staleTile.addEventListener('click', function () { toast('Em produção, isso filtraria a grade pelos artigos sem revisão há 90+ dias.'); });
    var pendTile = document.querySelector('.stat-tile.pending');
    if (pendTile) pendTile.addEventListener('click', function () { state.categoria = ''; state.setor = ''; state.busca = ''; document.getElementById('searchInput').value=''; setorSel.value=''; renderCatTabs(); renderGridPendingOnly(); });
  }

  function renderGridPendingOnly() {
    var list = ARTICLES.filter(function (a) { return a.status === 'rascunho'; });
    paintGrid(list);
  }

  function articleCardHtml(a) {
    var cat = CAT_BY_ID[a.categoria];
    var stale = a.status !== 'arquivado' && daysSince(a.atualizado) >= 90;
    return '' +
      '<div class="art-card" data-id="' + a.id + '" style="--cat-color:' + cat.color + ';">' +
        '<div class="art-card-top">' +
          '<span class="cat-badge"><span class="d"></span>' + cat.nome + '</span>' +
          (a.status !== 'publicado' ? '<span class="status-pill ' + a.status + '">' + (a.status === 'rascunho' ? 'Rascunho' : 'Arquivado') + '</span>' : '') +
        '</div>' +
        '<div class="art-card-title">' + escapeHtml(a.titulo) + '</div>' +
        '<div class="art-card-resumo">' + escapeHtml(a.resumo) + '</div>' +
        '<div class="art-card-meta">' +
          '<span class="setor-tag">' + escapeHtml(a.setor) + '</span>' +
          (stale ? '<span class="stale-tag"><svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="2"><circle cx="10" cy="10" r="7.3"/><path d="M10 6.5v4.2l3 1.8"/></svg>Sem revisão ' + fmtRelative(a.atualizado) + '</span>' : '<span>Atualizado ' + fmtRelative(a.atualizado) + '</span>') +
        '</div>' +
        '<div class="art-card-foot">' +
          '<span class="vote-mini"><span>👍 ' + a.util_positivo + '</span><span>👎 ' + a.util_negativo + '</span></span>' +
          '<span>' + a.visualizacoes + ' visualizações</span>' +
        '</div>' +
      '</div>';
  }

  function paintGrid(list) {
    var grid = document.getElementById('articleGrid');
    var empty = document.getElementById('emptyState');
    document.getElementById('resultCount').textContent = list.length + ' artigo(s)';
    if (list.length === 0) { grid.innerHTML = ''; empty.style.display = ''; return; }
    empty.style.display = 'none';
    grid.innerHTML = list.map(articleCardHtml).join('');
    Array.prototype.forEach.call(grid.querySelectorAll('.art-card'), function (card) {
      card.addEventListener('click', function () { openReadDrawer(card.dataset.id); });
    });
  }

  function renderGrid() {
    var list = ARTICLES.filter(passesFilter).sort(function (x, y) { return y.atualizado - x.atualizado; });
    paintGrid(list);
  }

  function renderAll() { renderCatTabs(); renderStats(); renderGrid(); }

  // ---------------- Drawer de leitura ----------------
  var readScrim = document.getElementById('drawerScrim');
  var readDrawer = document.getElementById('readDrawer');
  readScrim.addEventListener('click', closeReadDrawer);

  function closeReadDrawer() { readScrim.classList.remove('show'); readDrawer.classList.remove('show'); }

  function openReadDrawer(id) {
    var a = ARTICLES.find(function (x) { return x.id === id; });
    if (!a) return;
    a.visualizacoes++;
    var cat = CAT_BY_ID[a.categoria];
    var vote = state.myVotes[a.id];
    var canManage = state.role === 'admin';

    readDrawer.innerHTML = '' +
      '<div class="drawer-head">' +
        '<div>' +
          '<div class="badge-row" style="margin-bottom:6px;">' +
            '<span class="cat-badge" style="--cat-color:' + cat.color + ';"><span class="d"></span>' + cat.nome + '</span>' +
            (a.status !== 'publicado' ? '<span class="status-pill ' + a.status + '">' + (a.status === 'rascunho' ? 'Rascunho' : 'Arquivado') + '</span>' : '') +
            '<span class="setor-tag">' + escapeHtml(a.setor) + '</span>' +
          '</div>' +
          '<h2>' + escapeHtml(a.titulo) + '</h2>' +
          '<p>Por ' + (USERS[a.autor] || a.autor) + ' · atualizado ' + fmtRelative(a.atualizado) + ' · ' + a.visualizacoes + ' visualizações</p>' +
        '</div>' +
        '<button class="drawer-close" onclick="document.getElementById(\'drawerScrim\').classList.remove(\'show\');document.getElementById(\'readDrawer\').classList.remove(\'show\')"><svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M5 5l10 10M15 5L5 15"/></svg></button>' +
      '</div>' +
      '<div class="drawer-body">' +
        '<div class="md-content">' + renderMd(a.conteudo) + '</div>' +
        '<div class="feedback-box">' +
          '<span class="lbl">Isso ajudou você?</span>' +
          '<button class="vote-btn' + (vote === 'up' ? ' voted-up' : '') + '" id="voteUpBtn">👍 Sim (' + a.util_positivo + ')</button>' +
          '<button class="vote-btn' + (vote === 'down' ? ' voted-down' : '') + '" id="voteDownBtn">👎 Não (' + a.util_negativo + ')</button>' +
        '</div>' +
      '</div>' +
      '<div class="drawer-foot">' +
        (canManage ? (
          '<div>' + (a.status === 'rascunho' ? '<button class="btn-primary" id="publishBtn">Publicar</button>' : (a.status === 'publicado' ? '<button class="btn-ghost" id="archiveBtn">Arquivar</button>' : '<button class="btn-ghost" id="unarchiveBtn">Reativar</button>')) + '</div>'
        ) : '<div></div>') +
        '<div class="right">' +
          (canManage || a.autor === 'CR' ? '<button class="btn-ghost" id="editBtn">Editar</button>' : '') +
          (canManage ? '<button class="btn-danger" id="deleteBtn">Excluir</button>' : '') +
        '</div>' +
      '</div>';

    readScrim.classList.add('show');
    readDrawer.classList.add('show');
    renderStats(); // visualizações mudou

    document.getElementById('voteUpBtn').addEventListener('click', function () {
      if (state.myVotes[a.id] === 'up') return;
      if (state.myVotes[a.id] === 'down') a.util_negativo--;
      a.util_positivo++; state.myVotes[a.id] = 'up';
      openReadDrawer(id); toast('Valeu pelo feedback!');
    });
    document.getElementById('voteDownBtn').addEventListener('click', function () {
      if (state.myVotes[a.id] === 'down') return;
      if (state.myVotes[a.id] === 'up') a.util_positivo--;
      a.util_negativo++; state.myVotes[a.id] = 'down';
      openReadDrawer(id); toast('Obrigado — vamos revisar esse conteúdo.');
    });
    var publishBtn = document.getElementById('publishBtn');
    if (publishBtn) publishBtn.addEventListener('click', function () { a.status = 'publicado'; closeReadDrawer(); renderAll(); toast('Artigo publicado.'); });
    var archiveBtn = document.getElementById('archiveBtn');
    if (archiveBtn) archiveBtn.addEventListener('click', function () { a.status = 'arquivado'; closeReadDrawer(); renderAll(); toast('Artigo arquivado.'); });
    var unarchiveBtn = document.getElementById('unarchiveBtn');
    if (unarchiveBtn) unarchiveBtn.addEventListener('click', function () { a.status = 'publicado'; closeReadDrawer(); renderAll(); toast('Artigo reativado.'); });
    var editBtn = document.getElementById('editBtn');
    if (editBtn) editBtn.addEventListener('click', function () { closeReadDrawer(); openEditDrawer(a); });
    var deleteBtn = document.getElementById('deleteBtn');
    if (deleteBtn) deleteBtn.addEventListener('click', function () {
      if (!confirm('Excluir "' + a.titulo + '"?')) return;
      ARTICLES = ARTICLES.filter(function (x) { return x.id !== a.id; });
      closeReadDrawer(); renderAll(); toast('Artigo excluído.');
    });
  }

  // ---------------- Drawer de edição/criação ----------------
  var editScrim = document.getElementById('editScrim');
  var editDrawer = document.getElementById('editDrawer');
  editScrim.addEventListener('click', closeEditDrawer);
  document.getElementById('newArticleBtn').addEventListener('click', function () { openEditDrawer(null); });

  function closeEditDrawer() { editScrim.classList.remove('show'); editDrawer.classList.remove('show'); }

  function openEditDrawer(a) {
    var isNew = !a;
    var catOptions = CATEGORIAS.map(function (c) { return '<option value="' + c.id + '"' + (a && a.categoria === c.id ? ' selected' : '') + '>' + c.nome + '</option>'; }).join('');
    var setorOptions = SETORES.map(function (s) { return '<option value="' + s + '"' + (a && a.setor === s ? ' selected' : '') + '>' + s + '</option>'; }).join('');

    editDrawer.innerHTML = '' +
      '<div class="drawer-head">' +
        '<div><h2>' + (isNew ? 'Novo artigo' : 'Editar artigo') + '</h2><p>' + (state.role === 'vendedor' ? 'Salvo como rascunho — um admin/gestor revisa antes de publicar.' : 'Você pode publicar direto ou salvar como rascunho.') + '</p></div>' +
        '<button class="drawer-close" id="editCloseBtn"><svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M5 5l10 10M15 5L5 15"/></svg></button>' +
      '</div>' +
      '<form id="editForm">' +
      '<div class="drawer-body">' +
        '<div class="f-row-2">' +
          '<div class="f-group"><label class="f-label">Categoria <span class="req">*</span></label><select class="f-select" id="fCategoria">' + catOptions + '</select></div>' +
          '<div class="f-group"><label class="f-label">Setor</label><select class="f-select" id="fSetor">' + setorOptions + '</select></div>' +
        '</div>' +
        '<div class="f-group"><label class="f-label">Título <span class="req">*</span></label><input class="f-input" id="fTitulo" value="' + (a ? escapeHtml(a.titulo) : '') + '" placeholder="Ex.: Objeção — já tenho transportadora fixa" /></div>' +
        '<div class="f-group"><label class="f-label">Resumo</label><input class="f-input" id="fResumo" value="' + (a ? escapeHtml(a.resumo) : '') + '" placeholder="1 frase — aparece no card" /></div>' +
        '<div class="f-group"><label class="f-label">Tags</label><input class="f-input" id="fTags" value="' + (a ? escapeHtml(a.tags) : '') + '" placeholder="separadas por vírgula" /></div>' +
        '<div class="f-group">' +
          '<label class="f-label">Conteúdo <span class="req">*</span></label>' +
          '<textarea class="f-textarea big" id="fConteudo" placeholder="Use ## para título de seção, - para listas e **texto** para negrito">' + (a ? a.conteudo : '') + '</textarea>' +
          '<span class="f-hint">Markdown leve: <code>## Seção</code>, <code>- item de lista</code>, <code>**negrito**</code>.</span>' +
        '</div>' +
        '<div class="preview-card"><div class="preview-label">Prévia</div><div class="md-content" id="fPreview"></div></div>' +
      '</div>' +
      '<div class="drawer-foot">' +
        '<button type="button" class="btn-ghost" id="editCancelBtn">Cancelar</button>' +
        '<div class="right">' +
          (state.role === 'admin' ? '<button type="submit" class="btn-ghost" data-as="rascunho">Salvar como rascunho</button><button type="submit" class="btn-primary" data-as="publicado">Salvar e publicar</button>' : '<button type="submit" class="btn-primary" data-as="rascunho">Enviar para revisão</button>') +
        '</div>' +
      '</div>' +
      '</form>';

    editScrim.classList.add('show');
    editDrawer.classList.add('show');

    var contEl = document.getElementById('fConteudo');
    function updatePreview() { document.getElementById('fPreview').innerHTML = renderMd(contEl.value) || '<span style="color:var(--ink-faint);">A prévia aparece aqui conforme você digita…</span>'; }
    contEl.addEventListener('input', updatePreview);
    updatePreview();

    document.getElementById('editCloseBtn').addEventListener('click', closeEditDrawer);
    document.getElementById('editCancelBtn').addEventListener('click', closeEditDrawer);

    document.getElementById('editForm').addEventListener('submit', function (e) {
      e.preventDefault();
      var asStatus = document.activeElement && document.activeElement.dataset.as ? document.activeElement.dataset.as : 'rascunho';
      var titulo = document.getElementById('fTitulo').value.trim();
      var conteudo = contEl.value.trim();
      if (!titulo || !conteudo) { toast('Preencha título e conteúdo.'); return; }
      var payload = {
        categoria: document.getElementById('fCategoria').value,
        setor: document.getElementById('fSetor').value,
        titulo: titulo,
        resumo: document.getElementById('fResumo').value.trim(),
        tags: document.getElementById('fTags').value.trim(),
        conteudo: conteudo,
      };
      if (isNew) {
        ARTICLES.unshift(art(Object.assign(payload, { status: asStatus, autor: state.role === 'vendedor' ? 'CR' : 'DC', atualizado: new Date(TODAY) })));
        toast(asStatus === 'publicado' ? 'Artigo publicado.' : 'Rascunho enviado para revisão.');
      } else {
        Object.assign(a, payload, { status: asStatus, atualizado: new Date(TODAY) });
        toast('Artigo atualizado.');
      }
      closeEditDrawer();
      renderAll();
    });
  }

  // ---------------- Toast ----------------
  var toastTimer;
  function toast(msg) {
    var el = document.getElementById('toast');
    el.textContent = msg;
    el.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { el.classList.remove('show'); }, 2600);
  }

  // ---------------- Prévia no Dossiê (Fase 2) ----------------
  function renderDossierPreview() {
    var setor = 'Farma';
    var list = ARTICLES.filter(function (a) { return a.status === 'publicado' && (a.setor === setor || a.setor === 'Geral'); })
      .sort(function (x, y) { return (y.util_positivo - y.util_negativo) - (x.util_positivo - x.util_negativo); })
      .slice(0, 6);
    document.getElementById('dossierSugGrid').innerHTML = list.map(function (a) {
      var cat = CAT_BY_ID[a.categoria];
      return '<div class="sug-card" data-id="' + a.id + '" style="--cat-color:' + cat.color + ';"><div class="cat">' + cat.nome + '</div><div class="t">' + escapeHtml(a.titulo) + '</div><div class="r">' + escapeHtml(a.resumo) + '</div></div>';
    }).join('');
    Array.prototype.forEach.call(document.querySelectorAll('#dossierSugGrid .sug-card'), function (card) {
      card.addEventListener('click', function () { openReadDrawer(card.dataset.id); });
    });
  }

  renderAll();
