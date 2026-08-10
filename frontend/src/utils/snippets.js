// Expansão de snippet por #atalho — generalizado a partir da mecânica que já
// existia isolada na textarea de demonstração de SnippetsPage.jsx, pra poder
// ser usado em qualquer campo de roteiro (TaskModal, painel de ligação da
// fila de tarefas). Ver docs/PLANO_FILA_TAREFAS.md, Melhoria 2.

export function mergeSnippetVars(text, vars = {}) {
  return (text ?? '').replace(/\{\{(\w+)\}\}/g, (m, key) => vars[key] ?? m)
}

// Mesmo particionamento usado em SnippetsPage/ModelosEmailPage pra destacar só
// o valor mesclado numa prévia, sem dangerouslySetInnerHTML.
export function mergeSnippetVarsSegments(text, vars = {}) {
  const parts = []
  let lastIndex = 0
  const re = /\{\{(\w+)\}\}/g
  let m
  const source = text ?? ''
  while ((m = re.exec(source)) !== null) {
    if (m.index > lastIndex) parts.push({ text: source.slice(lastIndex, m.index), isVar: false })
    parts.push({ text: vars[m[1]] ?? m[0], isVar: Boolean(vars[m[1]]) })
    lastIndex = re.lastIndex
  }
  if (lastIndex < source.length) parts.push({ text: source.slice(lastIndex), isVar: false })
  return parts
}

/**
 * Handler de onChange pra um <textarea>/<input> controlado que expande
 * "#atalho " pro conteúdo do snippet correspondente (com variáveis já
 * mescladas) assim que o usuário digita o espaço depois do atalho.
 *
 * Uso: <textarea value={form.descricao} onChange={handleSnippetExpand(e, {
 *   value: form.descricao, onChange: set('descricao'), snippets, vars,
 * })} />
 *
 * Diferente da versão original (que mutava `el.value` direto, pensada pra um
 * textarea não-controlado de demonstração), esta versão sempre passa a string
 * final pro `onChange` do componente controlado — o valor exibido continua
 * vindo do estado do React, não do DOM.
 */
export function handleSnippetExpand(e, { onChange, snippets, vars = {} }) {
  const el = e.target
  const value = el.value
  onChange(value)

  if (e.nativeEvent?.data !== ' ') return
  const pos = el.selectionStart
  const before = value.slice(0, pos)
  const match = before.match(/#([a-z0-9]+) $/i)
  if (!match) return
  const atalho = match[1].toLowerCase()
  const snippet = (snippets ?? []).find((s) => s.atalho === atalho)
  if (!snippet) return

  const start = pos - match[0].length
  const replacement = mergeSnippetVars(snippet.conteudo, vars) + ' '
  const next = value.slice(0, start) + replacement + value.slice(pos)
  onChange(next)

  const newPos = start + replacement.length
  requestAnimationFrame(() => {
    if (document.activeElement !== el) return
    el.selectionStart = el.selectionEnd = newPos
  })
}

/** Insere o conteúdo (já mesclado) de um snippet na posição do cursor — usado
 * pelo botão "Inserir snippet" (sem precisar digitar o atalho). */
export function insertSnippetAtCursor(el, value, onChange, snippet, vars = {}) {
  const start = el?.selectionStart ?? value.length
  const end = el?.selectionEnd ?? value.length
  const insert = mergeSnippetVars(snippet.conteudo, vars)
  const next = value.slice(0, start) + insert + value.slice(end)
  onChange(next)
  const newPos = start + insert.length
  requestAnimationFrame(() => {
    if (!el) return
    el.focus()
    el.selectionStart = el.selectionEnd = newPos
  })
}
